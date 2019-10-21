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
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"fmt"

	"github.com/pkg/errors"
	"github.com/sapcc/go-vice"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/config"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
)

type viceClient struct {
	*vice.Client
	cfg    config.VicePresidentConfig
	logger log.Logger
}

func newViceClient(ssoCert tls.Certificate, cfg config.VicePresidentConfig, logger log.Logger) *viceClient {
	return &viceClient{
		Client: vice.New(ssoCert),
		cfg:    cfg,
		logger: logger,
	}
}

func (v *viceClient) createCSR(cert *ViceCertificate) error {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return errors.Wrapf(err, "couldn't generate private key")
	}

	csr, err := vice.CreateCSR(
		pkix.Name{
			CommonName:         cert.host,
			Country:            []string{v.cfg.Country},
			Province:           []string{v.cfg.Province},
			Locality:           []string{v.cfg.Locality},
			Organization:       []string{v.cfg.Organization},
			OrganizationalUnit: []string{v.cfg.OrganizationalUnit},
		},
		v.cfg.EMail,
		cert.getSANs(),
		key,
	)
	if err != nil {
		return errors.Wrapf(err, "couldn't create CSR")
	}
	cert.csr = csr
	cert.privateKey = key

	csrFilePath := fmt.Sprintf("%s/%s.csr", TmpPath, cert.host)
	keyFilePath := fmt.Sprintf("%s/%s.key", TmpPath, cert.host)
	v.logger.LogDebug("temporarily persisting CSR and key", "csrPath", csrFilePath, "keyPath", keyFilePath)

	_, err = saveToFile(cert.csr, csrFilePath)
	if err != nil {
		return err
	}

	keyByte, err := writePrivateKeyToPEM(cert.privateKey)
	if err != nil {
		return err
	}
	_, err = saveToFile(keyByte, keyFilePath)
	return err
}

func (v *viceClient) enroll(cert *ViceCertificate) error {
	if err := v.createCSR(cert); err != nil {
		return err
	}

	enrollment, err := v.Certificates.Enroll(
		context.TODO(),
		&vice.EnrollRequest{
			FirstName:          v.cfg.FirstName,
			LastName:           v.cfg.LastName,
			Email:              v.cfg.EMail,
			CSR:                string(cert.csr),
			Challenge:          v.cfg.DefaultChallenge,
			CertProductType:    vice.CertProductType.Server,
			ServerType:         vice.ServerType.OpenSSL,
			ValidityPeriod:     vice.ValidityPeriod.OneYear,
			SubjectAltNames:    cert.getSANs(),
			SignatureAlgorithm: vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)
	if err != nil {
		return errors.Wrapf(err, "couldn't enroll new certificate for host %v", cert.host)
	}
	// enrollment will only contain a cert if automatic approval is enabled
	if enrollment.Certificate != "" {
		if cert.certificate, err = readCertificateFromPEM([]byte(enrollment.Certificate)); err != nil {
			return errors.Wrapf(err, "failed to read certificate for host %v", cert.host)
		}
	}
	cert.tid = enrollment.TransactionID
	return nil
}

func (v *viceClient) renew(cert *ViceCertificate) error {
	if err := v.createCSR(cert); err != nil {
		return err
	}

	originalCertificate, err := writeCertificatesToPEM([]*x509.Certificate{cert.certificate})
	if err != nil {
		return errors.Wrapf(err, "failed to create certificate for host %s", cert.host)
	}
	originalCertificate = bytes.TrimSpace(originalCertificate)

	renewal, err := v.Certificates.Renew(
		context.TODO(),
		&vice.RenewRequest{
			FirstName:           v.cfg.FirstName,
			LastName:            v.cfg.LastName,
			Email:               v.cfg.EMail,
			CSR:                 string(cert.csr),
			SubjectAltNames:     cert.certificate.DNSNames,
			OriginalChallenge:   v.cfg.DefaultChallenge,
			Challenge:           v.cfg.DefaultChallenge,
			OriginalCertificate: string(originalCertificate),
			CertProductType:     vice.CertProductType.Server,
			ServerType:          vice.ServerType.OpenSSL,
			ValidityPeriod:      vice.ValidityPeriod.OneYear,
			SignatureAlgorithm:  vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)
	if err != nil {
		return errors.Wrapf(err, "couldn't renew certificate for host %v", cert.host)
	}
	// renewal will only contain a cert if automatic approval is enabled
	if renewal.Certificate != "" {
		if cert.certificate, err = readCertificateFromPEM([]byte(renewal.Certificate)); err != nil {
			return errors.Wrapf(err, "failed to read certificate for host %v", cert.host)
		}
	}
	cert.tid = renewal.TransactionID
	return nil
}

func (v *viceClient) pickup(cert *ViceCertificate) error {
	if cert.tid == "" {
		return fmt.Errorf("cannot pick up a certificate for host %v without its transaction ID", cert.host)
	}

	pickup, err := v.Certificates.Pickup(
		context.TODO(),
		&vice.PickupRequest{
			TransactionID: cert.tid,
		},
	)
	if err != nil {
		return errors.Wrapf(err, "couldn't pickup certificate for host %v with TID %s", cert.host, cert.tid)
	}

	pickedUpCert, err := readCertificateFromPEM([]byte(pickup.Certificate))
	if err != nil {
		return errors.Wrapf(err, "failed to read certificate for host %v", cert.host)
	}
	cert.certificate = pickedUpCert
	return nil
}

func (v *viceClient) approve(cert *ViceCertificate) error {
	if cert.tid == "" {
		return fmt.Errorf("cannot approve a certificate for host %s without its Transaction ID", cert.host)
	}
	approval, err := v.Certificates.Approve(
		context.TODO(),
		&vice.ApprovalRequest{
			TransactionID: cert.tid,
		},
	)
	if err != nil {
		return errors.Wrapf(err, "couldn't approve certificate for host %s using TID %s", cert.host, cert.tid)
	}
	if approval.Certificate == "" {
		return fmt.Errorf("approval didn't contain a certificate for host %s using TID %s", cert.host, cert.tid)
	}
	approvedCert, err := readCertificateFromPEM([]byte(approval.Certificate))
	if err != nil {
		return errors.Wrapf(err, "failed to read certificate for host %s", cert.host)
	}
	cert.certificate = approvedCert
	return nil
}

func (v *viceClient) replace(cert *ViceCertificate) error {
	if cert.csr == nil {
		if err := v.createCSR(cert); err != nil {
			return err
		}
	}

	originalCertificate, err := writeCertificatesToPEM([]*x509.Certificate{cert.certificate})
	if err != nil {
		return errors.Wrapf(err, "failed to create certificate for host %s", cert.host)
	}
	originalCertificate = bytes.TrimSpace(originalCertificate)

	replacement, err := v.Certificates.Replace(
		context.TODO(),
		&vice.ReplaceRequest{
			OriginalCertificate: string(originalCertificate),
			OriginalChallenge:   v.cfg.DefaultChallenge,
			Challenge:           v.cfg.DefaultChallenge,
			Reason:              ReasonSuperseded,
			CSR:                 string(cert.csr),
			FirstName:           v.cfg.FirstName,
			LastName:            v.cfg.LastName,
			Email:               v.cfg.EMail,
			ServerType:          vice.ServerType.OpenSSL,
			SignatureAlgorithm:  vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		},
	)

	// replacement will only contain a cert if automatic approval is enabled
	if replacement.Certificate != "" {
		if cert.certificate, err = readCertificateFromPEM([]byte(replacement.Certificate)); err != nil {
			return errors.Wrapf(err, "failed to read certificate for host %v", cert.host)
		}
	}
	cert.tid = replacement.TransactionID
	return nil
}
