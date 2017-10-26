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
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"net"
	"time"

	"github.com/sapcc/go-vice"
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
}

func (vc *ViceCertificate) enroll(vp *Operator) error {

	LogInfo("Enrolling certificate for host %s", vc.Host)

	if err := vc.createCSR(vp); err != nil {
		return err
	}

	enrollment, err := vp.ViceClient.Certificates.Enroll(
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
		return fmt.Errorf("Couldn't enroll new certificate for host %v using CSR %v: %s", vc.Host, string(vc.CSR), err)
	}

	// enrollment will only contain a cert if automatic approval is enabled
	if enrollment.Certificate != "" {
		if vc.Certificate, err = readCertificateFromPEM([]byte(enrollment.Certificate)); err != nil {
			return fmt.Errorf("Failed to read certificate for host %v: %s", vc.Host, err)
		}
	}

	vc.TID = enrollment.TransactionID

	return nil

}

func (vc *ViceCertificate) renew(vp *Operator) error {

	LogInfo("Renewing certificate for host %s", vc.Host)

	if err := vc.createCSR(vp); err != nil {
		return err
	}

	renewal, err := vp.ViceClient.Certificates.Renew(
		context.TODO(),
		&vice.RenewRequest{
			FirstName:          vp.VicePresidentConfig.FirstName,
			LastName:           vp.VicePresidentConfig.LastName,
			Email:              vp.VicePresidentConfig.EMail,
			CSR:                string(vc.CSR),
			SubjectAltNames:    vc.GetSANs(),
			OriginalChallenge:  vp.VicePresidentConfig.DefaultChallenge,
			Challenge:          vp.VicePresidentConfig.DefaultChallenge,
			CertProductType:    vice.CertProductType.Server,
			ServerType:         vice.ServerType.OpenSSL,
			ValidityPeriod:     vice.ValidityPeriod.OneYear,
			SignatureAlgorithm: vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)
	if err != nil {
		return fmt.Errorf("Couldn't renew certificate for host %v using CSR %v: %s", vc.Host, string(vc.CSR), err)
	}

	// renewal will only contain a cert if automatic approval is enabled
	if renewal.Certificate != "" {
		if vc.Certificate, err = readCertificateFromPEM([]byte(renewal.Certificate)); err != nil {
			return fmt.Errorf("Failed to read certificate for host %v: %v", vc.Host, err)
		}
	}

	vc.TID = renewal.TransactionID

	return nil

}

func (vc *ViceCertificate) pickup(vp *Operator) error {
	LogInfo("Picking up certificate for host %s", vc.Host)

	if vc.TID == "" {
		return fmt.Errorf("Cannot pick up a certificate for host %v without its Transaction ID",vc.Host)
	}

	pickup, err := vp.ViceClient.Certificates.Pickup(
		context.TODO(),
		&vice.PickupRequest{
			TransactionID: vc.TID,
		},
	)
	if err != nil {
		return fmt.Errorf("Couldn't pickup certificate for host %v with TID %s", vc.Host, vc.TID)
	}

	pickedUpCert, err := readCertificateFromPEM([]byte(pickup.Certificate))
	if err != nil {
		return fmt.Errorf("Failed to read certificate for host %v: %v", vc.Host, err)
	}
	vc.Certificate = pickedUpCert

	return nil
}

func (vc *ViceCertificate) approve(vp *Operator) error {

	LogInfo("Approving certificate for host %s using TID %s", vc.Host, vc.TID)

	if vc.TID == "" {
		return fmt.Errorf("Cannot approve a certificate for host %s without its Transaction ID",vc.Host)
	}

	approval, err := vp.ViceClient.Certificates.Approve(
		context.TODO(),
		&vice.ApprovalRequest{
			TransactionID: vc.TID,
		},
	)
	if err != nil {
		return fmt.Errorf("Couldn't approve certificate for host %s using TID %s", vc.Host, vc.TID)
	}

	if approval.Certificate == "" {
		return fmt.Errorf("Approval didn't contain a certificate for host %s using TID %s", vc.Host, vc.TID)
	}

	approvedCert, err := readCertificateFromPEM([]byte(approval.Certificate))
	if err != nil {
		return fmt.Errorf("Failed to read certificate for host %s: %v", vc.Host, err)
	}
	vc.Certificate = approvedCert

	return nil
}

func (vc *ViceCertificate) createCSR(vp *Operator) error {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return fmt.Errorf("Couldn't generate private key: %s", err)
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
		return fmt.Errorf("Couldn't create CSR: %s", err)
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
		LogError("Couldn't fetch remote certificate for %v: %v. Skipping...", vc.Host, err)
		return true
	}
	defer conn.Close()

	cert := conn.ConnectionState().PeerCertificates[0]
	if cert.Equal(vc.Certificate) {
		LogDebug("Remote certificate of host %v matches.", vc.Host)
	} else {
		LogInfo("Mismatching remote certificate. Expected host %v but got host %v", vc.Host, cert.Subject.CommonName)
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

func contains(stringSlice []string, searchString string) bool {
	for _, value := range stringSlice {
		if value == searchString {
			return true
		}
	}
	return false
}
