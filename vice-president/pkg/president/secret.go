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
	"fmt"
	"reflect"

	coreV1 "k8s.io/api/core/v1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
)

func newEmptySecret(nameSpace, name string, labels, annotations map[string]string) *coreV1.Secret {
	if labels == nil {
		labels = map[string]string{}
	}
	if annotations == nil {
		annotations = map[string]string{}
	}
	return &coreV1.Secret{
		Type: coreV1.SecretTypeOpaque,
		ObjectMeta: metaV1.ObjectMeta{
			Name:        name,
			Namespace:   nameSpace,
			Labels:      labels,
			Annotations: annotations,
		},
	}
}

// GetCertificateAndKeyFromSecret extracts the certificate and private key from a given secrets spec
func getCertificateAndKeyFromSecret(secret *coreV1.Secret, tlsKeySecretKey, tlsCertSecretKey string) (*x509.Certificate, *rsa.PrivateKey) {
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

func addCertificateAndKeyToSecret(viceCert *ViceCertificate, oldSecret *coreV1.Secret, tlsKeySecretKey, tlsCertSecretKey string) (*coreV1.Secret, error) {
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

func isSecretNeedsUpdate(sCur, sOld *coreV1.Secret) bool {
	// make sure to only trigger an update there are no empty values.
	// the ingress controller doesn't like this.
	for _, v := range sCur.Data {
		if v == nil {
			return false
		}
	}
	if !reflect.DeepEqual(sOld.Data, sCur.Data) {
		return true
	}
	return false
}

func isSecretAddedOrModified(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "secret"}, "")
	case watch.Added, watch.Modified:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func isSecretDeleted(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func secretKey(ingressNamespace, secretName string) string {
	return fmt.Sprintf("%s/%s", ingressNamespace, secretName)
}

// isSecretClaimedByAnotherIngress checks whether the given Secret is already claimed at all and if so by a different ingress than the one given.
func isSecretClaimedByAnotherIngress(secret *coreV1.Secret, ingressKey string) (string, bool) {
	if key, ok := secret.GetAnnotations()[AnnotationSecretClaimedByIngress]; ok {
		return key, key != ingressKey
	}
	// Not claimed.
	return "", false
}

func isSecretHasAnnotation(secret *coreV1.Secret, annotation string) bool {
	for _, ann := range secret.GetAnnotations() {
		if ann == annotation {
			return true
		}
	}
	return false
}
