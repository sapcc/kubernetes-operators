package k8sutils

import (
	"net/http"
	"time"

	crdutils "github.com/ant31/crd-validation/pkg"
	"github.com/pkg/errors"
	discoCRD "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco.stable.sap.cc"
	discoV1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco.stable.sap.cc/v1"
	extensionsobj "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1beta1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
)


func NewDiscoCRD() *extensionsobj.CustomResourceDefinition {
	return crdutils.NewCustomResourceDefinition(crdutils.Config{
		SpecDefinitionName:    "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco.stable.sap.cc/v1.DiscoRecord",
		EnableValidation:      true,
		ResourceScope:         string(extensionsobj.NamespaceScoped),
		Group:                 discoCRD.GroupName,
		Kind:                  discoV1.DiscoRecordKind,
		Version:               discoV1.Version,
		Plural:                discoV1.DiscoRecordKindPlural,
		GetOpenAPIDefinitions: discoV1.GetOpenAPIDefinitions,
	})
}

func WaitForDiscoCRDReady(listFunc func(opts metav1.ListOptions) (runtime.Object, error)) error {
	err := wait.Poll(3*time.Second, 10*time.Minute, func() (bool, error) {
		_, err := listFunc(metav1.ListOptions{})
		if err != nil {
			if se, ok := err.(*apierrors.StatusError); ok {
				if se.Status().Code == http.StatusNotFound {
					return false, nil
				}
			}
			return false, errors.Wrap(err, "failed to list CRD")
		}
		return true, nil
	})
	return errors.Wrap(err, "timed out while waiting for CRD")
}
