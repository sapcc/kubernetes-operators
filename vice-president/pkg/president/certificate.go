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

func (vc *ViceCertificate) enroll(vp *Operator) error {

	LogInfo("enrolling certificate for host %s", vc.Host)

	if err := vc.createCSR(vp); err != nil {
		return err
	}

	enrollment, err := vp.viceClient.Certificates.Enroll(
		context.TODO(),
		&vice.EnrollRequest{
			FirstName:          vp.VicePresidentConfig.FirstName,
			LastName:           vp.VicePresidentConfig.LastName,
			Email:              vp.VicePresidentConfig.EMail,
			CSR:                string(vc.CSR),
			Challenge:          vp.VicePresidentConfig.DefaultChallenge,
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

func (vc *ViceCertificate) renew(vp *Operator) error {
	LogInfo("renewing certificate for host %s", vc.Host)

	if err := vc.createCSR(vp); err != nil {
		return err
	}

	oc, err := writeCertificatesToPEM([]*x509.Certificate{vc.Certificate})
	if err != nil {
		return fmt.Errorf("failed to create certificate for host %s: %v", vc.Host, err)
	}
	b64EncByte, err := base64Encode(oc)
	if err != nil {
		return err
	}
	originalCertificate := string(b64EncByte)

	renewal, err := vp.viceClient.Certificates.Renew(
		context.TODO(),
		&vice.RenewRequest{
			FirstName:           vp.VicePresidentConfig.FirstName,
			LastName:            vp.VicePresidentConfig.LastName,
			Email:               vp.VicePresidentConfig.EMail,
			CSR:                 string(vc.CSR),
			SubjectAltNames:     vc.GetSANs(),
			OriginalChallenge:   vp.VicePresidentConfig.DefaultChallenge,
			Challenge:           vp.VicePresidentConfig.DefaultChallenge,
			OriginalCertificate: originalCertificate,
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

func (vc *ViceCertificate) pickup(vp *Operator) error {
	LogInfo("picking up certificate for host %s", vc.Host)

	if vc.TID == "" {
		return fmt.Errorf("cannot pick up a certificate for host %v without its Transaction ID", vc.Host)
	}

	pickup, err := vp.viceClient.Certificates.Pickup(
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

func (vc *ViceCertificate) approve(vp *Operator) error {

	LogInfo("approving certificate for host %s using TID %s", vc.Host, vc.TID)

	if vc.TID == "" {
		return fmt.Errorf("cannot approve a certificate for host %s without its Transaction ID", vc.Host)
	}

	approval, err := vp.viceClient.Certificates.Approve(
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

func (vc *ViceCertificate) createCSR(vp *Operator) error {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return fmt.Errorf("couldn't generate private key: %s", err)
	}

	csr, err := vice.CreateCSR(
		pkix.Name{
			CommonName:         vc.Host,
			Country:            []string{vp.VicePresidentConfig.Country},
			Province:           []string{vp.VicePresidentConfig.Province},
			Locality:           []string{vp.VicePresidentConfig.Locality},
			Organization:       []string{vp.VicePresidentConfig.Organization},
			OrganizationalUnit: []string{vp.VicePresidentConfig.OrganizationalUnit},
		},
		vp.VicePresidentConfig.EMail,
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
		LogError("failed to verify certificate for host %s: %s", vc.Host, err.Error())
		return false
	}
	return true
}

// DoesCertificateExpireSoon checks if a certificate is already expired or will expire within the next n month?
func (vc *ViceCertificate) DoesCertificateExpireSoon() bool {
	return !vc.Certificate.NotAfter.UTC().After(time.Now().UTC().AddDate(0, CertificateValidityMonth, 0))
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
		LogInfo("certificate and Key don't match: %s ", err)
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

	cert := conn.ConnectionState().PeerCertificates[0]

	if err := vc.compareRemoteCert(cert); err != nil {
		LogInfo(err.Error())
		return false
	}
	return true
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

func (vc *ViceCertificate) compareRemoteCert(remoteCert *x509.Certificate) error {
	if vc.Host != remoteCert.Subject.CommonName {
		return fmt.Errorf("mismatching host. expected %s, got %s", vc.Host, remoteCert.Subject.CommonName)
	}
	sort.Strings(vc.GetSANs())
	gotSANs := sort.StringSlice(remoteCert.DNSNames)
	sort.Strings(gotSANs)

	if !isStringSlicesEqual(vc.GetSANs(), gotSANs) {
		return fmt.Errorf("mismatching SANs. expected %v, got %v", vc.GetSANs(), gotSANs)
	}

	if !vc.Certificate.NotBefore.Equal(remoteCert.NotBefore) {
		return fmt.Errorf("mismatching validity: notBefore. expected %v, got %v", vc.Certificate.NotBefore, remoteCert.NotBefore)
	}

	if !vc.Certificate.NotAfter.Equal(remoteCert.NotAfter) {
		return fmt.Errorf("mismatching validity: notAfter. expected %v, got %v", vc.Certificate.NotAfter, remoteCert.NotAfter)
	}

	return nil
}

// SetIngressKey sets the ingress key <namespace>/<name>
func (vc *ViceCertificate) SetIngressKey(ingressNamespace, ingressName string) {
	vc.ingressKey = fmt.Sprintf("%s/%s", ingressNamespace, ingressName)
}

// GetIngressKey returns the ingress key <namespace>/<name>
func (vc *ViceCertificate) GetIngressKey() string {
	return vc.ingressKey
}
