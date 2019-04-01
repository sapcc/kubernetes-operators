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
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
)

type viceClient struct {
	*vice.Client
	config VicePresidentConfig
	logger log.Logger
}

func newViceClient(ssoCert tls.Certificate, config VicePresidentConfig, logger log.Logger) *viceClient {
	return &viceClient{
		Client: vice.New(ssoCert),
		config: config,
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
			Country:            []string{v.config.Country},
			Province:           []string{v.config.Province},
			Locality:           []string{v.config.Locality},
			Organization:       []string{v.config.Organization},
			OrganizationalUnit: []string{v.config.OrganizationalUnit},
		},
		v.config.EMail,
		cert.getSANs(),
		key,
	)
	if err != nil {
		return errors.Wrapf(err, "couldn't create CSR")
	}
	cert.csr = csr
	cert.privateKey = key

	filePath := fmt.Sprintf("%s/%s.csr", TmpPath, cert.host)
	v.logger.LogDebug("persisting CSR", "path", filePath)
	_, err = saveToFile(cert.csr, filePath)
	return err
}

func (v *viceClient) enroll(cert *ViceCertificate) error {
	if err := v.createCSR(cert); err != nil {
		return err
	}

	enrollment, err := v.Certificates.Enroll(
		context.TODO(),
		&vice.EnrollRequest{
			FirstName:          v.config.FirstName,
			LastName:           v.config.LastName,
			Email:              v.config.EMail,
			CSR:                string(cert.csr),
			Challenge:          v.config.DefaultChallenge,
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
			FirstName:           v.config.FirstName,
			LastName:            v.config.LastName,
			Email:               v.config.EMail,
			CSR:                 string(cert.csr),
			SubjectAltNames:     cert.certificate.DNSNames,
			OriginalChallenge:   v.config.DefaultChallenge,
			Challenge:           v.config.DefaultChallenge,
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
			OriginalChallenge:   v.config.DefaultChallenge,
			Challenge:           v.config.DefaultChallenge,
			Reason:              ReasonSuperseded,
			CSR:                 string(cert.csr),
			FirstName:           v.config.FirstName,
			LastName:            v.config.LastName,
			Email:               v.config.EMail,
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
