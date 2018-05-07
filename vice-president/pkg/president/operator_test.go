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
	"crypto/rand"
	"crypto/rsa"
	"io/ioutil"
	"path"
	"testing"

	"github.com/stretchr/testify/suite"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/tools/cache"
)

const (
	IngressName = "my-ingress"
	SecretName  = "my-secret"
	Namespace   = "default"
	HostName    = "example.com"
)

func TestMySuite(t *testing.T) {
	suite.Run(t, new(TestSuite))
}

func (s *TestSuite) TestGetCertificateFromSecret() {

	certificate, privateKey, err := s.VP.getCertificateAndKeyFromSecret(
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

	if err != nil {
		s.T().Errorf("Couldn't get certificate from secret: %s", err.Error())
	}

	s.Assert().Equal(s.Cert, certificate)
	s.Assert().Equal(s.Key, privateKey)

}

func (s *TestSuite) TestUpdateCertificateInSecret() {
	secret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      SecretName,
			Namespace: Namespace,
		},
	}

	updatedSecret, err := s.VP.addCertificateAndKeyToSecret(s.ViceCert, secret, SecretTLSKeyType, SecretTLSCertType)
	if err != nil {
		s.T().Error(err)
	}

	// verify
	certificate, privateKey, err := s.VP.getCertificateAndKeyFromSecret(updatedSecret, SecretTLSKeyType, SecretTLSCertType)
	if err != nil {
		s.T().Error(err)
	}

	s.Assert().Equal(s.ViceCert.Certificate, certificate)
	s.Assert().Equal(s.ViceCert.PrivateKey, privateKey)
}

func (s *TestSuite) TestEnrollCertificate() {

	if err := s.VP.enrollCertificate(s.ViceCert); err != nil {
		s.T().Error(err)
	}

	s.Assert().Equal("87d1adc3f1f262409092ec31fb09f4c7", s.ViceCert.TID)
}

func (s *TestSuite) TestRenewCertificate() {

	if err := s.VP.renewCertificate(s.ViceCert); err != nil {
		s.T().Error(err)
	}

	s.Assert().Equal("87d1adc3f1f262409092ec31fb09f4c7", s.ViceCert.TID)
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

	s.Assert().Equal(key, rKey)

}

func (s *TestSuite) TestIngressVicePresidentialAnnotation() {

	testData := map[bool]*v1beta1.Ingress{
		true: {
			ObjectMeta: metav1.ObjectMeta{
				Namespace: Namespace,
				Name:      "DoNotIgnoreMe!",
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
		s.Assert().Equal(expectedBool, s.VP.isTakeCareOfIngress(ingress))
	}

}

func (s *TestSuite) TestStateMachine() {

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
	key, err := cache.MetaNamespaceKeyFunc(ingress)
	if err != nil {
		s.T().Error(err)
	}

	s.VP.queue.Add(key)

	if err := s.VP.syncHandler(key); err != nil {
		// TODO: need to mock this
		if err.Error() != "the server could not find the requested resource (put secrets my-secret)" {
			//s.T().Error(err)
		}
	}
}

func (s *TestSuite) TestWriteCertificateChain() {

	expectedChainPEM, err := ioutil.ReadFile(path.Join(FIXTURES, "chain.pem"))

	chainPEM, err := writeCertificatesToPEM(
		s.ViceCert.WithIntermediateCertificate(),
	)
	if err != nil {
		s.T().Error(err)
	}

	//FIXME: actually this should equal
	s.Assert().Equal(expectedChainPEM, removeSpecialCharactersFromPEM(chainPEM))
}

func (s *TestSuite) TestRateLimitExceeded() {
	// set rate limit
	s.VP.VicePresidentConfig.RateLimit = 2
	hostName := "rateLimitedHost"
	vc := &ViceCertificate{
		Host: hostName,
	}
	vc.SetIngressKey(Namespace, IngressName)

	s.Assert().NoError(s.VP.enrollCertificate(vc))
	nReq, ok := s.VP.rateLimitMap.Load(hostName)
	s.Assert().True(ok)
	s.Assert().Equal(1, nReq.(int))

	s.Assert().NoError(s.VP.enrollCertificate(vc))
	nReq, ok = s.VP.rateLimitMap.Load(hostName)
	s.Assert().True(ok)
	s.Assert().Equal(2, nReq.(int))

	// 3rd enrollment is expected to be skipped since the limit of 2 requests for the host was reached.
	// this is logged and the number of requests is not incremented
	s.Assert().NoError(s.VP.enrollCertificate(vc))
	nReq, ok = s.VP.rateLimitMap.Load(hostName)
	s.Assert().True(ok)
	s.Assert().Equal(2, nReq.(int))
}
