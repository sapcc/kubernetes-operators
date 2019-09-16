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
	"crypto/rand"
	"crypto/rsa"
	"testing"

	"github.com/stretchr/testify/suite"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
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

func (s *TestSuite) TestEnrollCertificate() {
	err := s.VP.enrollCertificate(s.ViceCert)
	s.NoError(err, "there should be no error enrolling a new certificate")
	s.Equal("87d1adc3f1f262409092ec31fb09f4c7", s.ViceCert.tid)
}

func (s *TestSuite) TestRenewCertificate() {
	err := s.VP.renewCertificate(s.ViceCert)
	s.NoError(err, "there should be no error renewing a certificate")
	s.Equal("87d1adc3f1f262409092ec31fb09f4c7", s.ViceCert.tid)
}

func (s *TestSuite) TestApproveCertificate() {
	vc := s.ViceCert
	vc.tid = "87d1adc3f1f262409092ec31fb09f4c7"
	err := s.VP.approveCertificate(vc)
	s.NoError(err, "there should be no error approving a certificate")
}

func (s *TestSuite) TestPickupCertificate() {
	vc := s.ViceCert
	vc.tid = "87d1adc3f1f262409092ec31fb09f4c7"

	err := s.VP.pickupCertificate(s.ViceCert)
	s.NoError(err, "there should be no error picking up a certificate")
}

func (s *TestSuite) TestGenerateWriteReadPrivateKey() {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	s.Require().NoError(err, "there must be no error generating a private key")

	keyPEM, err := writePrivateKeyToPEM(key)
	s.NoError(err, "there should be no error writing a private key to PEM format")

	rKey, err := readPrivateKeyFromPEM(keyPEM)
	s.NoError(err, "there should be no error reading a private key from PEM format")

	s.Equal(key, rKey, "the keys should be equal after transformation to and from PEM format")
}

func (s *TestSuite) TestStateMachine() {
	ingress := &extensionsv1beta1.Ingress{
		ObjectMeta: metaV1.ObjectMeta{
			Namespace: Namespace,
			Name:      IngressName,
			Annotations: map[string]string{
				"vice-president": "true",
			},
		},
		Spec: extensionsv1beta1.IngressSpec{
			TLS: []extensionsv1beta1.IngressTLS{
				{
					Hosts:      []string{HostName},
					SecretName: SecretName,
				},
			},
		},
	}

	err := s.ResetIngressInformerStoreAndAddIngress(ingress)
	s.Require().NoError(err, "there must be no error resetting the ingress informer store")

	// Go for it: Secret doesn't exist. This should result in below error.
	key, err := cache.MetaNamespaceKeyFunc(ingress)
	s.Require().NoError(err, "there must be no error creating a key from an ingress")

	// Add the ingress to the queue bypassing the informers.
	s.VP.queue.Add(key)

	if err := s.VP.syncHandler(key); err != nil {
		// TODO: At least the state machine is triggered once.
		s.EqualError(err, "couldn't get nor create secret default/my-secret: couldn't create secret default/my-secret: the server could not find the requested resource (post secrets)")
	}
}

func (s *TestSuite) TestRateLimitExceeded() {
	// Set rate limit of 2, meaning the 3rd attempt for the same host must fail.
	s.VP.RateLimit = 2
	hostName := "rateLimitedHost"
	vc := &ViceCertificate{
		host: hostName,
		ingress: &extensionsv1beta1.Ingress{
			ObjectMeta: metaV1.ObjectMeta{
				Namespace: Namespace,
				Name:      IngressName,
			},
		},
	}
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
