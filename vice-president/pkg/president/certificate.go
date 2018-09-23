/*******************************************************************************
*
* Copyright 2017 SAP SE
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
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"sort"
	"strings"
	"time"

	"github.com/sapcc/go-vice"
	"golang.org/x/crypto/ocsp"
)

// ViceCertificate contains all properties requires by the Symantec VICE API
type ViceCertificate struct {
	Roots                   *x509.CertPool
	IntermediateCertificate *x509.Certificate
	Certificate             *x509.Certificate
	PrivateKey              *rsa.PrivateKey
	CSR                     []byte
	Host                    string
	sans                    []string
	TID                     string
	CACertificate           *x509.Certificate
	ocspServers             []string
	ingressKey              string
}

// NewViceCertificate returns a new vice certificate
func NewViceCertificate(host, ingressNamespace, ingressName string, sans []string, intermediateCertificate *x509.Certificate, roots *x509.CertPool) *ViceCertificate {
	vc := &ViceCertificate{
		Host: host,
		IntermediateCertificate: intermediateCertificate,
		Roots: roots,
	}
	vc.SetSANs(sans)
	vc.SetIngressKey(ingressNamespace, ingressName)
	return vc
}

func (vc *ViceCertificate) enroll(viceClient *vice.Client, config VicePresidentConfig) error {
	LogInfo("Enrolling certificate for host %s", vc.Host)
	if err := vc.createCSR(config); err != nil {
		return err
	}
	enrollment, err := viceClient.Certificates.Enroll(
		context.TODO(),
		&vice.EnrollRequest{
			FirstName:          config.FirstName,
			LastName:           config.LastName,
			Email:              config.EMail,
			CSR:                string(vc.CSR),
			Challenge:          config.DefaultChallenge,
			CertProductType:    vice.CertProductType.Server,
			ServerType:         vice.ServerType.OpenSSL,
			ValidityPeriod:     vice.ValidityPeriod.OneYear,
			SubjectAltNames:    vc.GetSANs(),
			SignatureAlgorithm: vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)
	if err != nil {
		return fmt.Errorf("couldn't enroll new certificate for host %v using CSR %v: %s", vc.Host, string(vc.CSR), err)
	}
	// enrollment will only contain a cert if automatic approval is enabled
	if enrollment.Certificate != "" {
		if vc.Certificate, err = readCertificateFromPEM([]byte(enrollment.Certificate)); err != nil {
			return fmt.Errorf("failed to read certificate for host %v: %s", vc.Host, err)
		}
	}
	vc.TID = enrollment.TransactionID

	return nil

}

func (vc *ViceCertificate) renew(viceClient *vice.Client, config VicePresidentConfig) error {
	LogInfo("Renewing certificate for host %s", vc.Host)
	if err := vc.createCSR(config); err != nil {
		return err
	}
	originalCertificate, err := writeCertificatesToPEM([]*x509.Certificate{vc.Certificate})
	if err != nil {
		return fmt.Errorf("failed to create certificate for host %s: %v", vc.Host, err)
	}
	originalCertificate = bytes.TrimSpace(originalCertificate)

	renewal, err := viceClient.Certificates.Renew(
		context.TODO(),
		&vice.RenewRequest{
			FirstName:           config.FirstName,
			LastName:            config.LastName,
			Email:               config.EMail,
			CSR:                 string(vc.CSR),
			SubjectAltNames:     vc.Certificate.DNSNames,
			OriginalChallenge:   config.DefaultChallenge,
			Challenge:           config.DefaultChallenge,
			OriginalCertificate: string(originalCertificate),
			CertProductType:     vice.CertProductType.Server,
			ServerType:          vice.ServerType.OpenSSL,
			ValidityPeriod:      vice.ValidityPeriod.OneYear,
			SignatureAlgorithm:  vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)
	if err != nil {
		return fmt.Errorf("couldn't renew certificate for host %v using CSR %v: %s", vc.Host, string(vc.CSR), err)
	}
	// renewal will only contain a cert if automatic approval is enabled
	if renewal.Certificate != "" {
		if vc.Certificate, err = readCertificateFromPEM([]byte(renewal.Certificate)); err != nil {
			return fmt.Errorf("failed to read certificate for host %v: %v", vc.Host, err)
		}
	}
	vc.TID = renewal.TransactionID

	return nil

}

func (vc *ViceCertificate) pickup(viceClient *vice.Client, config VicePresidentConfig) error {
	LogInfo("Picking up certificate for host %s", vc.Host)

	if vc.TID == "" {
		return fmt.Errorf("cannot pick up a certificate for host %v without its Transaction ID", vc.Host)
	}

	pickup, err := viceClient.Certificates.Pickup(
		context.TODO(),
		&vice.PickupRequest{
			TransactionID: vc.TID,
		},
	)
	if err != nil {
		return fmt.Errorf("couldn't pickup certificate for host %v with TID %s", vc.Host, vc.TID)
	}

	pickedUpCert, err := readCertificateFromPEM([]byte(pickup.Certificate))
	if err != nil {
		return fmt.Errorf("failed to read certificate for host %v: %v", vc.Host, err)
	}
	vc.Certificate = pickedUpCert

	return nil
}

func (vc *ViceCertificate) approve(viceClient *vice.Client, config VicePresidentConfig) error {
	LogInfo("Approving certificate for host %s using TID %s", vc.Host, vc.TID)
	if vc.TID == "" {
		return fmt.Errorf("cannot approve a certificate for host %s without its Transaction ID", vc.Host)
	}
	approval, err := viceClient.Certificates.Approve(
		context.TODO(),
		&vice.ApprovalRequest{
			TransactionID: vc.TID,
		},
	)
	if err != nil {
		return fmt.Errorf("couldn't approve certificate for host %s using TID %s", vc.Host, vc.TID)
	}
	if approval.Certificate == "" {
		return fmt.Errorf("approval didn't contain a certificate for host %s using TID %s", vc.Host, vc.TID)
	}
	approvedCert, err := readCertificateFromPEM([]byte(approval.Certificate))
	if err != nil {
		return fmt.Errorf("failed to read certificate for host %s: %v", vc.Host, err)
	}
	vc.Certificate = approvedCert

	return nil
}

func (vc *ViceCertificate) replace(viceClient *vice.Client, config VicePresidentConfig) error {
	LogInfo("Replacing certificate for host %s", vc.Host)
	if vc.CSR == nil {
		if err := vc.createCSR(config); err != nil {
			return err
		}
	}

	originalCertificate, err := writeCertificatesToPEM([]*x509.Certificate{vc.Certificate})
	if err != nil {
		return fmt.Errorf("failed to create certificate for host %s: %v", vc.Host, err)
	}
	originalCertificate = bytes.TrimSpace(originalCertificate)

	replacement, err := viceClient.Certificates.Replace(
		context.TODO(),
		&vice.ReplaceRequest{
			OriginalCertificate: string(originalCertificate),
			OriginalChallenge:   config.DefaultChallenge,
			Challenge:           config.DefaultChallenge,
			Reason:              "SUPERSEDED",
			CSR:                 string(vc.CSR),
			FirstName:           config.FirstName,
			LastName:            config.LastName,
			Email:               config.EMail,
			ServerType:          vice.ServerType.OpenSSL,
			SignatureAlgorithm:  vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)

	// replacement will only contain a cert if automatic approval is enabled
	if replacement.Certificate != "" {
		if vc.Certificate, err = readCertificateFromPEM([]byte(replacement.Certificate)); err != nil {
			return fmt.Errorf("failed to read certificate for host %v: %v", vc.Host, err)
		}
	}
	vc.TID = replacement.TransactionID
	return nil
}

func (vc *ViceCertificate) createCSR(config VicePresidentConfig) error {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return fmt.Errorf("couldn't generate private key: %s", err)
	}

	csr, err := vice.CreateCSR(
		pkix.Name{
			CommonName:         vc.Host,
			Country:            []string{config.Country},
			Province:           []string{config.Province},
			Locality:           []string{config.Locality},
			Organization:       []string{config.Organization},
			OrganizationalUnit: []string{config.OrganizationalUnit},
		},
		config.EMail,
		vc.GetSANs(),
		key,
	)
	if err != nil {
		return fmt.Errorf("couldn't create CSR: %s", err)
	}

	vc.CSR = csr
	vc.PrivateKey = key

	return nil

}

// DoesCertificateAndHostMatch checks that a given certificate is for the correct host
func (vc *ViceCertificate) DoesCertificateAndHostMatch() bool {
	if err := vc.Certificate.VerifyHostname(vc.Host); err != nil {
		LogError("Failed to verify certificate for host %s: %s", vc.Host, err.Error())
		return false
	}
	return true
}

// DoesCertificateExpireSoon checks if a certificate is already expired or will expire within the next n month?
func (vc *ViceCertificate) DoesCertificateExpireSoon(minCertValidityDays int) bool {
	certExpiry := vc.Certificate.NotAfter.UTC()
	shouldBeValidUntil := time.Now().UTC().AddDate(0, 0, minCertValidityDays)
	return certExpiry.Before(shouldBeValidUntil)
}

// DoesKeyAndCertificateTally checks if a given private key is for the correct certificate
func (vc *ViceCertificate) DoesKeyAndCertificateTally() bool {

	certBlock := pem.Block{
		Type:  CertificateType,
		Bytes: vc.Certificate.Raw,
	}

	keyBlock := pem.Block{
		Type:  PrivateKeyType,
		Bytes: x509.MarshalPKCS1PrivateKey(vc.PrivateKey),
	}

	if _, err := tls.X509KeyPair(pem.EncodeToMemory(&certBlock), pem.EncodeToMemory(&keyBlock)); err != nil {
		LogInfo("Certificate and Key don't match: %s ", err)
		return false
	}
	return true
}

// DoesRemoteCertificateMatch connects to the URL, does the TLS handshake and checks if the certificates match
func (vc *ViceCertificate) DoesRemoteCertificateMatch() bool {
	conn, err := tls.DialWithDialer(
		&net.Dialer{Timeout: 2 * time.Second},
		"tcp",
		fmt.Sprintf("%v:%v", vc.Host, 443),
		&tls.Config{InsecureSkipVerify: true},
	)
	if err != nil {
		LogError("couldn't fetch remote certificate for %v: %v. Skipping", vc.Host, err)
		return true
	}
	defer conn.Close()

	remoteCert := conn.ConnectionState().PeerCertificates[0]

	// in case we get the kubernetes fake certificate from the ingress controller break here and do nothing but log this
	if isIngressFakeCertificate(remoteCert) {
		LogInfo("tried to reach %v, but the ingress controller returned the %v", vc.Host, IngressFakeCN)
		// TODO: surface this properly
		return true
	}

	return vc.compareRemoteCert(remoteCert)
}

// GetSANs returns the SANs of the certificate. Also checks if the common name is part of the SANs.
func (vc *ViceCertificate) GetSANs() []string {
	if vc.sans == nil {
		vc.sans = []string{}
	}
	if contains(vc.sans, vc.Host) != true {
		vc.sans = append(vc.sans, vc.Host)
	}
	return vc.sans
}

// GetSANsString returns the concatenated list of SANs
func (vc *ViceCertificate) GetSANsString() string {
	return strings.Join(vc.GetSANs(), ",")
}

// SetSANs set the SANs of the certificate. Also checks if the common name is part of the SANs.
func (vc *ViceCertificate) SetSANs(sans []string) {
	if contains(sans, vc.Host) != true {
		sans = append(sans, vc.Host)
	}
	if vc.sans == nil {
		vc.sans = sans
	} else {
		vc.sans = append(vc.sans, sans...)
	}
}

// WithIntermediateCertificate returns the certificate chain
func (vc *ViceCertificate) WithIntermediateCertificate() []*x509.Certificate {
	if vc.IntermediateCertificate != nil {
		return []*x509.Certificate{
			vc.Certificate,
			vc.IntermediateCertificate,
		}
	}
	return []*x509.Certificate{
		vc.Certificate,
	}
}

// IsRevoked checks whether the certificate was revoked using OCSP (Online Certificate Status Protocol)
func (vc *ViceCertificate) IsRevoked() bool {
	if err := vc.getRootCA(); err != nil {
		LogError(err.Error())
		return false
	}

	if err := vc.getOCSPURIs(); err != nil {
		LogError(err.Error())
		return false
	}

	for _, uri := range vc.ocspServers {
		ocspResponse, err := vc.issueOCSPRequest(uri)
		if err != nil {
			LogError("ocsp check for host %s failed: %v", vc.Host, err.Error())
			return false
		}

		if ocspResponse.Status == ocsp.Revoked {
			LogInfo("certificate for host %s was revoked at %v. reason: %v", vc.Host, ocspResponse.RevokedAt, ocspRevokationReasonToString(ocspResponse.RevocationReason))
			return true
		}
		LogDebug("certificate for host %v is %v", vc.Host, ocspStatusToString(ocspResponse.Status))
	}

	return false
}

func (vc *ViceCertificate) issueOCSPRequest(ocspURI string) (*ocsp.Response, error) {
	ocspRequest, e := ocsp.CreateRequest(vc.Certificate, vc.CACertificate, nil)
	if e != nil {
		LogError(e.Error())
	}
	ocspRequestReader := bytes.NewReader(ocspRequest)
	httpResponse, err := http.Post(ocspURI, "application/ocsp-request", ocspRequestReader)
	defer httpResponse.Body.Close()
	if err != nil {
		return nil, err
	}

	ocspResponseBytes, err := ioutil.ReadAll(httpResponse.Body)
	if err != nil {
		return nil, err
	}

	return ocsp.ParseResponse(ocspResponseBytes, vc.CACertificate)
}

func (vc *ViceCertificate) getOCSPURIs() error {
	ocspServers := vc.Certificate.OCSPServer
	if ocspServers != nil {
		vc.ocspServers = ocspServers
		return nil
	}
	return fmt.Errorf("failed to get OCSP URIs. certificate OCSP URI is %v", ocspServers)
}

func (vc *ViceCertificate) getRootCA() error {
	caIssuerURIList := vc.Certificate.IssuingCertificateURL
	if caIssuerURIList == nil || len(caIssuerURIList) == 0 {
		return fmt.Errorf("failed to get CA Issuer URI. certificate CA Issuer URI is %v", vc.Certificate.IssuingCertificateURL)
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

	vc.CACertificate = ca
	return nil
}

func (vc *ViceCertificate) compareRemoteCert(remoteCert *x509.Certificate) bool {
	// FIXME: remoteCert.Equal(vc.Certificate) is to error-prone :-/

	if vc.Host != remoteCert.Subject.CommonName {
		LogInfo("mismatching host. expected %s, got %s", vc.Host, remoteCert.Subject.CommonName)
		return false
	}

	sort.Strings(vc.GetSANs())
	gotSANs := sort.StringSlice(remoteCert.DNSNames)
	sort.Strings(gotSANs)
	if !isStringSlicesEqual(vc.GetSANs(), gotSANs) {
		LogInfo("mismatching SANs. expected %v, got %v", vc.GetSANs(), gotSANs)
		return false
	}

	if !vc.Certificate.NotBefore.UTC().Equal(remoteCert.NotBefore.UTC()) {
		LogInfo("mismatching validity: notBefore. expected %v, got %v", vc.Certificate.NotBefore, remoteCert.NotBefore)
		return false
	}

	if !vc.Certificate.NotAfter.UTC().Equal(remoteCert.NotAfter.UTC()) {
		LogInfo("mismatching validity: notAfter. expected %v, got %v", vc.Certificate.NotAfter, remoteCert.NotAfter)
		return false
	}

	return true
}

// SetIngressKey sets the ingress key <namespace>/<name>
func (vc *ViceCertificate) SetIngressKey(ingressNamespace, ingressName string) {
	vc.ingressKey = fmt.Sprintf("%s/%s", ingressNamespace, ingressName)
}

// GetIngressKey returns the ingress key <namespace>/<name>
func (vc *ViceCertificate) GetIngressKey() string {
	return vc.ingressKey
}

// isIngressFakeCertificate determines whether the remote certificate is the fake certificate send by the ingress controller
func isIngressFakeCertificate(certificate *x509.Certificate) bool {
	return certificate.Subject.CommonName == IngressFakeCN && contains(certificate.DNSNames, IngressFakeHost)
}
