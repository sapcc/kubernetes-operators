package president

import (
	"reflect"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
)

// isIngressNeedsUpdate determines whether an ingress is outdated an should be updated base on changes to .spec.tls or annotations
func isIngressNeedsUpdate(iCur, iOld *v1beta1.Ingress) bool {
	if !reflect.DeepEqual(iCur.Spec.TLS, iOld.Spec.TLS) || isIngressAnnotationChanged(iCur, iOld) {
		return true
	}
	return false
}

func isIngressAnnotationChanged(iCur, iOld *v1beta1.Ingress) bool {
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

func isAnnotationRemoved(iCur, iOld *v1beta1.Ingress, annotation string) bool {
	return isIngressHasAnnotation(iOld, annotation) && !isIngressHasAnnotation(iCur, annotation)
}

func isIngressHasAnnotation(ingress *v1beta1.Ingress, annotation string) bool {
	return ingress.GetAnnotations()[annotation] == "true"
}

// isLastHostInIngressSpec checks if 'hostName' is the last host in ingress.Spec.TLS
func isLastHostInIngressSpec(ingress *v1beta1.Ingress, hostName string) bool {
	lastHost := ingress.Spec.TLS[len(ingress.Spec.TLS)-1].Hosts
	if lastHost != nil && len(lastHost) >= 1 {
		// CN is lastHost[0], SANs are lastHost[1:]
		return lastHost[0] == hostName
	}
	return false
}

func ingressGetSecretKeysFromAnnotation(ingress *v1beta1.Ingress) (tlsKeySecretKey, tlsCertSecretKey string) {
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
		return false, apierrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
	}
	switch ing := event.Object.(type) {
	case *v1beta1.Ingress:
		return !isIngressHasAnnotation(ing, AnnotationCertificateReplacement), nil
	}
	return false, nil
}
