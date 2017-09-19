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
	"path"
	"testing"

	"crypto/rand"
	"crypto/rsa"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/kubernetes/pkg/util/slice"
)

const (
  IngressName = "my-ingress"
  SecretName = "my-secret"
  Namespace = "default"
  HostName = "example.com"
)

func TestMySuite(t *testing.T) {
	suite.Run(t, new(TestSuite))
}

func (s *TestSuite) TestGetCertificateFromSecret() {

	certificate, privateKey, err := s.VP.getCertificateAndKeyFromSecret(s.Secret)
	if err != nil {
		s.T().Errorf("Couldn't get certificate from secret: %s", err.Error())
	}

	assert.Equal(s.T(), s.Cert, certificate)
	assert.Equal(s.T(), s.Key, privateKey)

}

func (s *TestSuite) TestUpdateCertificateInSecret() {
	secret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      SecretName,
			Namespace: Namespace,
		},
	}

	updatedSecret, err := s.VP.addCertificateAndKeyToSecret(s.ViceCert, secret)
	if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), s.Secret.Data[SecretTLSCertType], updatedSecret.Data[SecretTLSCertType])

	// verify
	certificate, privateKey, err := s.VP.getCertificateAndKeyFromSecret(updatedSecret)
	if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), s.ViceCert.Certificate, certificate)
	assert.Equal(s.T(), s.ViceCert.PrivateKey, privateKey)
}

func (s *TestSuite) TestCertificateAndHostMatch() {

	s.ViceCert.Host = "invalid.com"
	assert.False(s.T(), s.ViceCert.DoesCertificateAndHostMatch())

	s.ViceCert.Host = "example.com"
	assert.True(s.T(), s.ViceCert.DoesCertificateAndHostMatch())
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

func (s *TestSuite) TestGenerateWriteReadPrivateKey() {
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

	assert.Equal(s.T(), key, rKey)

}

func (s *TestSuite) TestLoadConfig() {
	config, err := ReadConfig(path.Join(FIXTURES, "example.vicepresidentconfig"))
	if err != nil {
		s.T().Error(err)
	}
	assert.Equal(s.T(), "Max", config.FirstName)
	assert.Equal(s.T(), "Muster", config.LastName)
	assert.Equal(s.T(), 5, config.ResyncPeriod)
	assert.Equal(s.T(), 60, config.CertificateCheckInterval)
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

func (s *TestSuite) TestIngressVicePresidentialAnnotation() {

  testData := map[bool]*v1beta1.Ingress{
    true: {
      ObjectMeta: metav1.ObjectMeta{
        Namespace:   Namespace,
        Name:        "DoNotIgnoreMe!",
        Annotations: map[string]string{
          "vice-president": "true",
        },
      },
    },
    false: {
      ObjectMeta: metav1.ObjectMeta{
        Namespace:   Namespace,
        Name:        "IgnoreMe!",
        Annotations: map[string]string{},
      },
    },
  }

  for expectedBool, ingress := range testData {
    assert.Equal(s.T(), expectedBool, s.VP.isTakeCareOfIngress(ingress))
  }

}

func (s *TestSuite) TestStateMachine() {

	ingress := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      IngressName,
			Annotations: map[string]string{
        "vice-president" : "true",
			},
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
				{
					Hosts:      []string{HostName},
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
		// TODO: need to mock this
		if err.Error() != "the server could not find the requested resource (put secrets my-secret)" {
			s.T().Error(err)
		}
	}
}
