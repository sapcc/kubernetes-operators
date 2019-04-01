/*******************************************************************************
*
* Copyright 2019 SAP SE
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You should have received a copy of the License along with this
* program. If not, you may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
*******************************************************************************/

package president

import (
	"bytes"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"sort"
	"strings"
	"time"

	"github.com/pkg/errors"
	"golang.org/x/crypto/ocsp"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
)

// ViceCertificate contains all properties requires by the Symantec VICE API
type ViceCertificate struct {
	roots                   *x509.CertPool
	intermediateCertificate *x509.Certificate
	certificate             *x509.Certificate
	privateKey              *rsa.PrivateKey
	csr                     []byte
	host                    string
	sans                    []string
	tid                     string
	caCertificate           *x509.Certificate
	ocspServers             []string
	ingress                 *v1beta1.Ingress
	secretName              string
}

// NewViceCertificate returns a new vice certificate.
func NewViceCertificate(ingress *v1beta1.Ingress, secretName, host string, sans []string, intermediateCertificate *x509.Certificate, rootCertificates *x509.CertPool) *ViceCertificate {
	vc := &ViceCertificate{
		ingress:                 ingress,
		secretName:              secretName,
		intermediateCertificate: intermediateCertificate,
		roots:                   rootCertificates,
		host:                    host,
	}
	vc.setSANs(sans)
	return vc
}

// DoesCertificateAndHostMatch checks that a given certificate is for the correct host
func (vc *ViceCertificate) DoesCertificateAndHostMatch() bool {
	if err := vc.certificate.VerifyHostname(vc.host); err != nil {
		return false
	}
	return true
}

// DoesCertificateExpireSoon checks if a certificate is already expired or will expire within the next n month?
func (vc *ViceCertificate) DoesCertificateExpireSoon(minCertValidityDays int) bool {
	certExpiry := vc.certificate.NotAfter.UTC()
	shouldBeValidUntil := time.Now().UTC().AddDate(0, 0, minCertValidityDays)
	return certExpiry.Before(shouldBeValidUntil)
}

// DoesKeyAndCertificateTally checks if a given private key is for the correct certificate
func (vc *ViceCertificate) DoesKeyAndCertificateTally() bool {

	certBlock := pem.Block{
		Type:  CertificateType,
		Bytes: vc.certificate.Raw,
	}

	keyBlock := pem.Block{
		Type:  PrivateKeyType,
		Bytes: x509.MarshalPKCS1PrivateKey(vc.privateKey),
	}

	if _, err := tls.X509KeyPair(pem.EncodeToMemory(&certBlock), pem.EncodeToMemory(&keyBlock)); err != nil {
		return false
	}
	return true
}

// DoesRemoteCertificateMatch connects to the URL, does the TLS handshake and checks if the certificates match
func (vc *ViceCertificate) DoesRemoteCertificateMatch() bool {
	conn, err := tls.DialWithDialer(
		&net.Dialer{Timeout: 2 * time.Second},
		"tcp",
		fmt.Sprintf("%v:%v", vc.host, 443),
		&tls.Config{InsecureSkipVerify: true},
	)
	if err != nil {
		return true
	}
	defer conn.Close()

	remoteCert := conn.ConnectionState().PeerCertificates[0]

	// in case we get the kubernetes fake certificate from the ingress controller break here and do nothing but log this
	if isIngressFakeCertificate(remoteCert) {
		// TODO: surface this properly
		return true
	}

	return vc.compareRemoteCert(remoteCert)
}

// getSANs returns the SANs of the certificate. Also checks if the common name is part of the SANs.
func (vc *ViceCertificate) getSANs() []string {
	if vc.sans == nil {
		vc.sans = []string{}
	}
	if contains(vc.sans, vc.host) != true {
		vc.sans = append(vc.sans, vc.host)
	}
	return vc.sans
}

// getSANsString returns the concatenated list of SANs.
func (vc *ViceCertificate) getSANsString() string {
	return strings.Join(vc.getSANs(), ",")
}

// setSANs set the SANs of the certificate. Also checks if the common name is part of the SANs.
func (vc *ViceCertificate) setSANs(sans []string) {
	if contains(sans, vc.host) != true {
		sans = append(sans, vc.host)
	}
	if vc.sans == nil {
		vc.sans = sans
	} else {
		vc.sans = append(vc.sans, sans...)
	}
}

// withIntermediateCertificate returns the certificate chain.
func (vc *ViceCertificate) withIntermediateCertificate() []*x509.Certificate {
	if vc.intermediateCertificate != nil {
		return []*x509.Certificate{
			vc.certificate,
			vc.intermediateCertificate,
		}
	}
	return []*x509.Certificate{
		vc.certificate,
	}
}

// IsRevoked checks whether the certificate was revoked using OCSP (Online Certificate Status Protocol)
func (vc *ViceCertificate) IsRevoked() bool {
	if err := vc.getRootCA(); err != nil {
		return false
	}

	if err := vc.getOCSPURIs(); err != nil {
		return false
	}

	for _, uri := range vc.ocspServers {
		if uri == "" {
			continue
		}

		ocspResponse, err := vc.issueOCSPRequest(uri)
		if err != nil {
			return false
		}

		if ocspResponse.Status == ocsp.Revoked {
			return true
		}
	}

	return false
}

func (vc *ViceCertificate) issueOCSPRequest(ocspURI string) (*ocsp.Response, error) {
	ocspRequest, err := ocsp.CreateRequest(vc.certificate, vc.caCertificate, &ocsp.RequestOptions{})
	if err != nil {
		return nil, errors.Wrap(err, "failed to create OCSP request")
	}

	ocspRequestReader := bytes.NewReader(ocspRequest)
	httpResponse, err := http.Post(ocspURI, "application/ocsp-request", ocspRequestReader)
	defer httpResponse.Body.Close()
	if err != nil {
		return nil, err
	}

	ocspResponseBytes, err := ioutil.ReadAll(httpResponse.Body)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read request body")
	}
	return ocsp.ParseResponse(ocspResponseBytes, vc.caCertificate)
}

func (vc *ViceCertificate) getOCSPURIs() error {
	ocspServers := vc.certificate.OCSPServer
	if ocspServers != nil {
		vc.ocspServers = ocspServers
		return nil
	}
	return fmt.Errorf("failed to get OCSP URIs. certificate OCSP URI is %v", ocspServers)
}

func (vc *ViceCertificate) getRootCA() error {
	caIssuerURIList := vc.certificate.IssuingCertificateURL
	if caIssuerURIList == nil || len(caIssuerURIList) == 0 {
		return fmt.Errorf("failed to get CA Issuer URI. certificate CA Issuer URI is %v", vc.certificate.IssuingCertificateURL)
	}

	caIssuerURI := caIssuerURIList[0]
	fileName := getFileNameFromURI(caIssuerURI)
	filePath := TmpPath + fileName

	var certByte []byte
	certByte, err := ioutil.ReadFile(filePath)
	if err != nil {
		certByte, err = downloadAndPersistFile(caIssuerURI, filePath)
		if err != nil {
			return err
		}
	}

	ca, err := x509.ParseCertificate(certByte)
	if err != nil {
		return err
	}

	vc.caCertificate = ca
	return nil
}

func (vc *ViceCertificate) compareRemoteCert(remoteCert *x509.Certificate) bool {
	// FIXME: remoteCert.Equal(vc.certificate) is too error-prone :-/

	if vc.host != remoteCert.Subject.CommonName {
		return false
	}

	sort.Strings(vc.getSANs())
	gotSANs := sort.StringSlice(remoteCert.DNSNames)
	sort.Strings(gotSANs)
	if !isStringSlicesEqual(vc.getSANs(), gotSANs) {
		return false
	}

	if !vc.certificate.NotBefore.UTC().Equal(remoteCert.NotBefore.UTC()) {
		return false
	}

	if !vc.certificate.NotAfter.UTC().Equal(remoteCert.NotAfter.UTC()) {
		return false
	}

	return true
}

func (vc *ViceCertificate) getIngressKey() string {
	return fmt.Sprintf("%s/%s", vc.ingress.GetNamespace(), vc.ingress.GetName())
}

func (vc *ViceCertificate) getSecretKey() string {
	return fmt.Sprintf("%s/%s", vc.ingress.GetNamespace(), vc.secretName)
}

// isIngressFakeCertificate determines whether the remote certificate is the fake certificate send by the ingress controller
func isIngressFakeCertificate(certificate *x509.Certificate) bool {
	return certificate.Subject.CommonName == IngressFakeCN && contains(certificate.DNSNames, IngressFakeHost)
}
