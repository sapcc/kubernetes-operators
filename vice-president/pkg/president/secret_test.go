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
	coreV1 "k8s.io/api/core/v1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func (s *TestSuite) TestUpdateCertificateInSecret() {
	secret := &coreV1.Secret{
		ObjectMeta: metaV1.ObjectMeta{
			Name:      SecretName,
			Namespace: Namespace,
		},
	}

	// add
	updatedSecret, err := addCertificateAndKeyToSecret(s.ViceCert, secret, SecretTLSKeyType, SecretTLSCertType)
	s.NoError(err, "there should be no error storing the certificate and key in the secret")

	// verify
	certificate, privateKey := getCertificateAndKeyFromSecret(updatedSecret, SecretTLSKeyType, SecretTLSCertType)
	s.Equal(s.ViceCert.certificate, certificate, "the retrieved certificate should be equal to the one initially stored in the secret")
	s.Equal(s.ViceCert.privateKey, privateKey, "the retrieved private key should be equal to the one initially stored in the secret")
}

func (s *TestSuite) TestGetCertificateFromSecret() {
	certificate, privateKey := getCertificateAndKeyFromSecret(
		&coreV1.Secret{
			ObjectMeta: metaV1.ObjectMeta{
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

	s.Equal(s.Cert, certificate, "should be equal to the certificate from the secret")
	s.Equal(s.Key, privateKey, "should be equal to the private key from the secret")
}
