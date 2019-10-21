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
	"crypto/rsa"
	"crypto/x509"
	corev1 "k8s.io/api/core/v1"
)

// getCertificateAndKeyFromSecret extracts the certificate and private key from a given secrets spec
func getCertificateAndKeyFromSecret(secret *corev1.Secret, tlsKeySecretKey, tlsCertSecretKey string) (*x509.Certificate, *rsa.PrivateKey) {
	var (
		certificate *x509.Certificate
		privateKey  *rsa.PrivateKey
	)

	if secret.Data == nil {
		return nil, nil
	}

	if k, ok := secret.Data[tlsKeySecretKey]; ok && len(k) > 0 {
		key, err := readPrivateKeyFromPEM(k)
		if err != nil {
			return nil, nil
		}
		privateKey = key
	}

	if c, ok := secret.Data[tlsCertSecretKey]; ok && len(c) > 0 {
		cert, err := readCertificateFromPEM(c)
		if err != nil {
			// Private key found in secret. We might be able to pickup the certificate.
			return nil, privateKey
		}
		certificate = cert
	}

	return certificate, privateKey
}

// addCertificateAndKeyToSecret adds the given certificate and private key to the secret.
func addCertificateAndKeyToSecret(viceCert *ViceCertificate, oldSecret *corev1.Secret, tlsKeySecretKey, tlsCertSecretKey string) (*corev1.Secret, error) {
	certPEM, err := writeCertificatesToPEM(viceCert.withIntermediateCertificate())
	if err != nil {
		return nil, err
	}
	keyPEM, err := writePrivateKeyToPEM(viceCert.privateKey)
	if err != nil {
		return nil, err
	}

	secret := oldSecret.DeepCopy()
	if secret.Data == nil {
		secret.Data = map[string][]byte{}
	}

	secret.Data[tlsCertSecretKey] = removeSpecialCharactersFromPEM(certPEM)
	secret.Data[tlsKeySecretKey] = removeSpecialCharactersFromPEM(keyPEM)

	return secret, nil
}

// isSecretClaimedByAnotherIngress checks whether the given Secret is already claimed at all and if so by a different ingress than the one given.
func isSecretClaimedByAnotherIngress(secret *corev1.Secret, ingressKey string) (string, bool) {
	if key, ok := secret.GetAnnotations()[AnnotationSecretClaimedByIngress]; ok {
		return key, key != ingressKey
	}
	// Not claimed.
	return "", false
}
