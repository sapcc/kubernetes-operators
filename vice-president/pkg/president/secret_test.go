package president

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/pkg/api/v1"
)

func (s *TestSuite) TestUpdateCertificateInSecret() {
	secret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      SecretName,
			Namespace: Namespace,
		},
	}

	// add
	updatedSecret, err := addCertificateAndKeyToSecret(s.ViceCert, secret, SecretTLSKeyType, SecretTLSCertType)
	s.NoError(err, "there should be no error storing the certificate and key in the secret")

	// verify
	certificate, privateKey, err := getCertificateAndKeyFromSecret(updatedSecret, SecretTLSKeyType, SecretTLSCertType)
	s.NoError(err, "there should be no error retrieving the certificate and key from the secret")

	s.Equal(s.ViceCert.certificate, certificate, "the retrieved certificate should be equal to the one initially stored in the secret")
	s.Equal(s.ViceCert.privateKey, privateKey, "the retrieved private key should be equal to the one initially stored in the secret")
}

func (s *TestSuite) TestGetCertificateFromSecret() {
	certificate, privateKey, err := getCertificateAndKeyFromSecret(
		&v1.Secret{
			ObjectMeta: metav1.ObjectMeta{
				Namespace: Namespace,
				Name:      SecretName,
			},
			Data: map[string][]byte{
				SecretTLSCertType: s.CertByte,
				SecretTLSKeyType:  s.KeyByte,
			},
		},
		SecretTLSKeyType, SecretTLSCertType,
	)
	s.NoError(err, "there should be no error retrieving the certificate and key from the secret")
	s.Equal(s.Cert, certificate, "should be equal to the certificate from the secret")
	s.Equal(s.Key, privateKey, "should be equal to the private key from the secret")

}
