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

package k8sutils

import (
	"reflect"

	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
)

// IngressHasAnnotation checks whether the given ingres has the annotation.
func IngressHasAnnotation(ingress *extensionsv1beta1.Ingress, annotation string) bool {
	if val, ok := ingress.GetAnnotations()[annotation]; ok {
		return val == "true"
	}
	return false
}

// IsLastHostInIngressSpec checks if 'hostName' is the last host in ingress.Spec.TLS
func IsLastHostInIngressSpec(ingress *extensionsv1beta1.Ingress, hostName string) bool {
	lastHost := ingress.Spec.TLS[len(ingress.Spec.TLS)-1].Hosts
	if lastHost != nil && len(lastHost) >= 1 {
		// CN is lastHost[0], SANs are lastHost[1:]
		return lastHost[0] == hostName
	}
	return false
}

// IngressGetSecretKeysFromAnnotation ....
func IngressGetSecretKeysFromAnnotation(ingress *extensionsv1beta1.Ingress, defaultSecretTLSKeyType, defaultSecretTLSCertType string) (tlsKeySecretKey, tlsCertSecretKey string) {
	tlsKeySecretKey = defaultSecretTLSKeyType
	tlsCertSecretKey = defaultSecretTLSCertType

	if keySecretKey, ok := ingress.GetAnnotations()["vice-president/tls-key-secret-key"]; ok {
		tlsKeySecretKey = keySecretKey
	}
	if certSecretkey, ok := ingress.GetAnnotations()["vice-president/tls-cert-secret-key"]; ok {
		tlsCertSecretKey = certSecretkey
	}
	return tlsKeySecretKey, tlsCertSecretKey
}

// IngressHasDeletionTimestamp checks whether the ingress has a deletion timestamp set.
func IngressHasDeletionTimestamp(ingress *extensionsv1beta1.Ingress) bool {
	return ingress.GetDeletionTimestamp() != nil
}

// IngressHasFinalizer checks whether the given ingress has a finalizer.
func IngressHasFinalizer(ingress *extensionsv1beta1.Ingress, finalizer string) bool {
	for _, fin := range ingress.GetFinalizers() {
		if fin == finalizer {
			return true
		}
	}
	return false
}

func isIngressAddedOrModified(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
	case watch.Added, watch.Modified:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func isIngressNeedsUpdate(old, new *extensionsv1beta1.Ingress) bool {
	// Ingress needs update if spec or annotations changed or deletionTimestamp was added.
	if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
		return true
	}
	return false
}
