package president

import (
	"fmt"
	"path"
	"testing"

	"crypto/rand"
	"crypto/rsa"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes/fake"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/kubernetes/pkg/util/slice"
)

const IngressName = "my-ingress"
const SecretName = "my-secret"
const Namespace = "default"

func TestMySuite(t *testing.T) {
	suite.Run(t, new(TestSuite))
}

func (s *TestSuite) TestGetCertificateFromSecret() {

	viceCert, err := s.VP.getCertificateAndKeyFromSecret(s.Secret)
	if err != nil {
		s.T().Errorf("Couldn't get certificate from secret: %s", err.Error())
	}

	assert.Equal(s.T(), s.Cert, viceCert.Certificate)
	assert.Equal(s.T(), s.Key, viceCert.PrivateKey)

}

func (s *TestSuite) TestUpdateCertificateInSecret() {
	secret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
      Name: SecretName,
      Namespace: Namespace,
    },
	}

	updatedSecret, err := s.VP.addCertificateAndKeyToSecret(s.ViceCert, secret)
  if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), s.Secret.Data[SecretTLSCertType], updatedSecret.Data[SecretTLSCertType])
  // TODO:
  //assert.Equal(s.T(), s.Secret.Data[SecretTLSKeyType], updatedSecret.Data[SecretTLSKeyType])

  // verify
  viceCert, err := s.VP.getCertificateAndKeyFromSecret(updatedSecret)
  if err != nil {
    s.T().Error(err)
  }
  assert.Equal(s.T(), s.ViceCert.Certificate, viceCert.Certificate)
  assert.Equal(s.T(), s.ViceCert.PrivateKey, viceCert.PrivateKey)
}

func (s *TestSuite) TestCertificateAndHostMatch() {

	s.ViceCert.Host = "invalid.com"
	assert.False(s.T(), s.ViceCert.DoesCertificateAndHostMatch())
}

func (s *TestSuite) TestDoesKeyAndCertificateTally() {

	randomKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		s.T().Errorf("Couldn't generate random key. %s", err.Error())
	}

	assert.True(s.T(), s.ViceCert.DoesKeyAndCertificateTally())

	s.ViceCert.PrivateKey = randomKey
	assert.False(s.T(), s.ViceCert.DoesKeyAndCertificateTally())

}

func (s *TestSuite) TestDoesCertificateExpireSoon() {

	assert.False(s.T(), s.ViceCert.DoesCertificateExpireSoon())

}

func (s *TestSuite) TestEnrollCertificate() {

	if err := s.VP.enrollCertificate(s.ViceCert); err != nil {
		s.T().Error(err)
	}
}

func (s *TestSuite) TestRenewCertificate() {

	if err := s.VP.renewCertificate(s.ViceCert); err != nil {
		s.T().Error(err)
	}
}

func (s *TestSuite) TestApproveCertificate() {

	vc := s.ViceCert
	vc.TID = "87d1adc3f1f262409092ec31fb09f4c7"

	if err := s.VP.approveCertificate(vc); err != nil {
		s.T().Error(err)
	}
}

func (s *TestSuite) TestPickupCertificate() {

	vc := s.ViceCert
	vc.TID = "87d1adc3f1f262409092ec31fb09f4c7"

	if err := s.VP.pickupCertificate(vc); err != nil {
		s.T().Error(err)
	}
}

func (s *TestSuite) TestIngressSetState() {
	expectedIng := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      IngressName,
			Namespace: Namespace,
			Annotations: map[string]string{
				"example.com/vice-president-state": "enroll",
			},
		},
	}

	fk := fake.NewSimpleClientset(expectedIng)

	ing := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      IngressName,
			Namespace: Namespace,
		},
	}

	annotatedIng, err := s.VP.ingressSetAnnotation(ing, "example.com/vice-president-state", IngressStateEnroll)
	if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), expectedIng.GetAnnotations(), annotatedIng.GetAnnotations())

	updatedIng, err := fk.ExtensionsV1beta1().Ingresses(Namespace).Update(annotatedIng)
	if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), expectedIng.GetAnnotations(), updatedIng.GetAnnotations())

}

func (s *TestSuite) GenerateWriteReadPrivateKey() {
  key, err := rsa.GenerateKey(rand.Reader, 2048)
  if err != nil {
    s.T().Error(err)
  }

  keyPEM, err := writePrivateKeyToPEM(key)
  if err != nil {
    s.T().Error(err)
  }

  rKey, err := readPrivateKeyFromPEM(keyPEM)
  if err != nil {
    s.T().Error(err)
  }

  assert.Equal(s.T(),key,rKey)

}

func (s *TestSuite) TestIngressSetStateAndTIDAnnotation() {
	Host := "example.com"
	ing := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      IngressName,
			Namespace: Namespace,
		},
	}

	updatedStateIng := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      IngressName,
			Namespace: Namespace,
			Annotations: map[string]string{
				fmt.Sprintf("%s/s", Host, IngressStateAnnotation): IngressStateEnroll,
			},
		},
	}

	assert.Equal(s.T(), IngressStateEnroll, s.VP.ingressGetStateAnnotationForHost(updatedStateIng, Host))
	assert.True(s.T(), s.VP.isIngressNeedsUpdate(updatedStateIng, ing))

	ing.SetAnnotations(map[string]string{fmt.Sprintf("%s/%s", Host, IngressStateAnnotation): IngressStateApprove})
	assert.Equal(s.T(), IngressStateApprove, s.VP.ingressGetStateAnnotationForHost(ing, Host))

	ing.SetAnnotations(map[string]string{fmt.Sprintf("%s/%s", Host, IngressTIDAnnotation): "uniqueTID"})
	assert.Equal(s.T(), "uniqueTID", s.VP.ingressGetTIDForHost(ing, Host))
}

func (s *TestSuite) TestLoadConfig() {
	config, err := ReadConfig(path.Join(FIXTURES, "example.vicepresidentconfig"))
	if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), "Max", config.FirstName)
	assert.Equal(s.T(), "Muster", config.LastName)
	assert.Equal(s.T(), 5, config.ResyncPeriod)
	assert.Equal(s.T(), 15, config.CertificateCheckInterval)
}

func (s *TestSuite) TestGetSANS() {
	testViceCertificates := map[*ViceCertificate][]string{
		&ViceCertificate{}:                                                      {""},
		&ViceCertificate{Host: ""}:                                              {""},
		&ViceCertificate{Host: "example.com"}:                                   {"example.com"},
		&ViceCertificate{Host: "example.com", SANs: []string{"my-example.com"}}: {"example.com", "my-example.com"},
	}

	for viceCert, expectedSANS := range testViceCertificates {
		assert.Equal(s.T(),
			slice.SortStrings(expectedSANS),
			slice.SortStrings(viceCert.GetSANs()),
		)
	}
}

func (s *TestSuite) TestSkipIngressWithoutVicePresidentialAnnotation() {

	ingress := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace:   Namespace,
			Name:        "IgnoreMe!",
			Annotations: map[string]string{},
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
				{
					Hosts:      []string{"example.com"},
					SecretName: SecretName,
				},
			},
		},
	}

	if err := s.ResetIngressInformerStoreAndAddIngress(ingress); err != nil {
		s.T().Error(err)
	}

	if err := s.ResetSecretInformerStoreAndAddSecret(nil); err != nil {
		s.T().Error(err)
	}

	if err := s.VP.syncHandler(ingress); err != nil {
		s.T().Error(err)
	}
	o, _, _ := s.VP.IngressInformer.GetStore().Get(ingress)
	ing := o.(*v1beta1.Ingress)

	// neither state nor tid should be annotated

	assert.Empty(s.T(), ing.GetAnnotations())
	assert.Empty(s.T(), s.VP.SecretInformer.GetStore().List())

}

// TestIngressStatemachineNewCreateSecretEnrollApproveCert tests the behaviour if the referenced secret doesn't exist, in which case it should be created and enrollment of the cert should be triggered.
func (s *TestSuite) TestIngressStatemachineNewCreateSecretEnrollCert() {

	Host := "example.com"

	ingress := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      IngressName,
			Annotations: map[string]string{
				"vice-president": "true",
			},
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
				{
					Hosts:      []string{Host},
					SecretName: SecretName,
				},
			},
		},
	}

	if err := s.ResetIngressInformerStoreAndAddIngress(ingress); err != nil {
		s.T().Error(err)
	}

	// go for it. secret doesn't exist. this should result in below error. also the state should have changed to IngressStateEnroll
	if err := s.VP.syncHandler(ingress); err != nil {
		s.T().Error(err)
	}
}

// TestIngressStatemachineIngressTIDAnnotationEmptySecretExistsPickupCert tests the behaviour if the ingress is annotated with a Transaction ID, but the secret wasn't updated with the cert. Pickup should be triggered.
func (s *TestSuite) TestIngressStatemachineIngressTIDAnnotationEmptySecretExistsPickupCert() {

	Host := "example.com"
	tidAnnotationKey := fmt.Sprintf("%s/%s", Host, IngressTIDAnnotation)

	ingress := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      IngressName,
			Annotations: map[string]string{
				"vice-president": "true",
				tidAnnotationKey: "87d1adc3f1f262409092ec31fb09f4c7",
			},
		},
		TypeMeta: metav1.TypeMeta{
			APIVersion: "extensions/v1beta1",
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
				{
					Hosts:      []string{Host},
					SecretName: SecretName,
				},
			},
		},
	}

	secret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      SecretName,
		},
		TypeMeta: metav1.TypeMeta{
			APIVersion: "v1",
		},
		Data: map[string][]byte{
			"tls.crt": {},
			"tls.key": []byte("LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFb3dJQkFBS0NBUUVBc3JEWEtja1p4ZS9PZVhPdnlYNVpId0hPMDlDZDBLekpiSG56STJCazY0VnEyeDBzCmlYTVpzdVVLQitrZUVjZXNReENKL1JoQ0NiYlBzN3JjSzhUTmRNTnBacnJ6bWJHT3JJSWowUWkvaTJsZ3lpKzQKN3VQdlo5NnlOVVI5a0hoMGV3TUtzRDc2WkRQTkxrUTg4Y1ZwNU83VjdJTHR4ZnU2VG8raExMZmR6Tm85K3ErRQp5aC9iYnZ3N3l4VU5iRzJBUGV2cWJSWE5SZk9jLy9WTGRyY0FpczEzVWloOC9sVEw0RFNOSVBJczJIK0NTN2MrCklHMUJidXBUQ1NPL051SHJxMVpEZ1ZOTzVpenNRanJ5dEhTd09RbHZ4c2Q5TkxJYzZvV2ZIRkJVd0hET05tZisKRkRVTTZLTjRzRUFoOEliSzVTOXZSVGJMcEJjcldrN05QK1QydlFJREFRQUJBb0lCQUFFZUxocHEwYWgxV1p0VQo1L0tnd2JuNTd1dFFVTXh2YUVzdmNCLzJpR3NZeUpSYVdGNzd3MXRsSjJ6cFBuRHFDTi9haUtKMnRtTU5LN3Q2CkhjcUFUckMrVURoK1R1dlZPb2xGdnllZG9HVWs0YUFpTUV2K1RROGZTNG9keFpOVHpaYS9iQit5SlNyZlVCZE0KQWYyWk9KSmdGQ0tJcHlnbjdRQjAwWk5RQ3lrdTZhaXA5ekhRSG9XcXJtUVZLaFNoOGttUEpLbzlpYStnaGNsRwppK3h0V1A0UnlHV1R4OW42MEVicWVxR0JqMkpGcVFBdzUwTDRzVWYrQmZkNTM5R3h5VmJXTmY0eFROTmRYRTlLCjZHVXIzQXlkeUkwSU5ncGF1bi90QmNDRW41K3NZd3pta2VkMjNzaXUrSzhWRGZGMXF2UzdIQzU4WVEvWk1GRmgKcE41MlY4RUNnWUVBNlZrbk5za25JQXd6M2Q5ci9TekVYVzNPdFpTWUh5a09jbEFzOUt6SmtTZ2V0MVIrVjFwTQpVY1QrUXp4UFhSck5EMVF1SjgybUs5aDVibVBUeTRWWkpnVDcvTmtBMXA5eHptK0t3V2t0b05KOTZJUG5rOThuClBCbDV6QXg0N0xqUUFOQVVwc2Y0QW9NazY2a05DNlRiVHBmb0lOeWcxQkQrNENJc2E2b05YZGtDZ1lFQXhBbHEKYkJ6ZmpCRGNUN1Q5NE92NXUza09GTU1pa0tuZ2liaFE5TWFpM3VRU1hIenQ4QmZCSXR4TkRMWlAxaGIxRnFacwp0UDhqVmhpL2w0aXdqRkJnS21seGZCcG5FRFpoYUZlTUxEL2hKWlRhdUxRSnMwaVRGaHNGeUJ3WVFTSFlpNmkvCmUzMjB4TDVQZmdKZUozVWZYTlZhdDQ3eXFNSmtYWmhRYmdHNnZZVUNnWUVBelIzWklvZGZKUVNVOHd0WjJZcG8KY2RmOFJCRUNSeUhIMlNRdzRFS2lURDZBQVpiOEY3MEFLVUNJWUlHN0laUlZmSXY2cG5KWEIyT2FHamNXRFdpQwpITEYwNzZXdzN2ZjVDZ1Z5YXVFUmdyU0VpTWFwNFluZTZ5MVpxc3VyNENuMGJVSjdaTCtTZW1MZEtXbklWZHZzCkN3SHN3all1Q1R1SFQyMjZya2treHNFQ2dZQWhEbUZtcDV1K2Q1MWV4MnRFQVNhVVNUNXBtOW41UU52Ky9SaVIKbmVrYTRxU0IrZ0w1U0ZnbDg3WCtYY09xbXlacTBsZGtVZDE0aUNYT2ZKc2duZkVKVmN4d0c5ZWpNVGhOcXUyVgpESlIvak5FdzhoTHNxMkU2Q2daNGp0dzhKMlBuY09ZUkFjcDRub3F5K2QwOGxCQmN6QkZIQUpERWlqcjRXVlcrCnB3WUJMUUtCZ0FxSmZ0YnhqeGo5dkloYW9lYTQzM1pBRXh4eTJ3QS9WekZaa3FJSlM2YTBsOTJOOHMvcWZDWGUKc3dqK3pJSEZKTGxyNDJ2SE5FbWtuemJDS0xRUjNWWlF6b09TWmVTRTE1N1hHeDM0c29FU1QwbDRqNUhlbjlOSgpOS2tGbjBRSGkxa1RDMnVlR2daUCtkYjRpMGlHbmJ3RVUvYXJkTlFSbUo1UkZsT0pMOTRpCi0tLS0tRU5EIFJTQSBQUklWQVRFIEtFWS0tLS0tCg=="),
		},
		Type: v1.SecretTypeOpaque,
	}

	if err := s.ResetIngressInformerStoreAndAddIngress(ingress); err != nil {
		s.T().Error(err)
	}

	if err := s.ResetSecretInformerStoreAndAddSecret(secret); err != nil {
		s.T().Error(err)
	}

	if err := s.VP.syncHandler(ingress); err != nil {
		s.T().Error(err)
	}

	// check the secret
	obj, _, _ := s.VP.SecretInformer.GetStore().Get(secret)
	sec := obj.(*v1.Secret)
	assert.Equal(s.T(), secret.Data["tls.key"], sec.Data["tls.key"])
	assert.True(s.T(), sec.Data["tls.crt"] != nil)
}
