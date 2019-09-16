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
	"reflect"

	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
)

// isIngressNeedsUpdate determines whether an ingress is outdated an should be updated base on changes to .spec.tls or annotations
func isIngressNeedsUpdate(iCur, iOld *extensionsv1beta1.Ingress) bool {
	if !reflect.DeepEqual(iCur.Spec.TLS, iOld.Spec.TLS) || isIngressAnnotationChanged(iCur, iOld) {
		return true
	}
	return false
}

func isIngressAnnotationChanged(iCur, iOld *extensionsv1beta1.Ingress) bool {
	// ignore removal of vice-president/replace-cert annotation
	if isAnnotationRemoved(iCur, iOld, AnnotationCertificateReplacement) {
		// was that the only change? copy to new map to avoid changing the original
		iOldAnnotations := map[string]string{}
		for k, v := range iOld.GetAnnotations() {
			if k != AnnotationCertificateReplacement {
				iOldAnnotations[k] = v
			}
		}
		return !reflect.DeepEqual(iOldAnnotations, iCur.GetAnnotations())
	}
	return !reflect.DeepEqual(iOld.GetAnnotations(), iCur.GetAnnotations())
}

func isAnnotationRemoved(iCur, iOld *extensionsv1beta1.Ingress, annotation string) bool {
	return isIngressHasAnnotation(iOld, annotation) && !isIngressHasAnnotation(iCur, annotation)
}

func isIngressHasAnnotation(ingress *extensionsv1beta1.Ingress, annotation string) bool {
	if val, ok := ingress.GetAnnotations()[annotation]; ok {
		return val == "true"
	}
	return false
}

// isLastHostInIngressSpec checks if 'hostName' is the last host in ingress.Spec.TLS
func isLastHostInIngressSpec(ingress *extensionsv1beta1.Ingress, hostName string) bool {
	lastHost := ingress.Spec.TLS[len(ingress.Spec.TLS)-1].Hosts
	if lastHost != nil && len(lastHost) >= 1 {
		// CN is lastHost[0], SANs are lastHost[1:]
		return lastHost[0] == hostName
	}
	return false
}

func ingressGetSecretKeysFromAnnotation(ingress *extensionsv1beta1.Ingress) (tlsKeySecretKey, tlsCertSecretKey string) {
	tlsKeySecretKey = SecretTLSKeyType
	tlsCertSecretKey = SecretTLSCertType

	if keySecretKey, ok := ingress.GetAnnotations()[AnnotationTLSKeySecretKey]; ok {
		tlsKeySecretKey = keySecretKey
	}
	if certSecretkey, ok := ingress.GetAnnotations()[AnnotationTLSCertSecretKey]; ok {
		tlsCertSecretKey = certSecretkey
	}
	return tlsKeySecretKey, tlsCertSecretKey
}

func isIngressAnnotationRemoved(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
	}
	switch ing := event.Object.(type) {
	case *extensionsv1beta1.Ingress:
		return !isIngressHasAnnotation(ing, AnnotationCertificateReplacement), nil
	}
	return false, nil
}

func isVicePresidentFinalizerRemoved(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
	}
	switch ing := event.Object.(type) {
	case *extensionsv1beta1.Ingress:
		return !ingressHasVicePresidentFinalizer(ing), nil
	}
	return false, nil
}

func ingressHasDeletionTimestamp(ingress *extensionsv1beta1.Ingress) bool {
	return ingress.GetDeletionTimestamp() == nil
}

func ingressHasVicePresidentFinalizer(ingress *extensionsv1beta1.Ingress) bool {
	for _, fin := range ingress.GetFinalizers() {
		if fin == FinalizerVicePresident {
			return true
		}
	}
	return false
}
