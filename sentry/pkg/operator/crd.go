package operator

import (
	"context"
	"reflect"
	"time"

	apiextensionsv1 "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	apiutilerrors "k8s.io/apimachinery/pkg/util/errors"
	"k8s.io/apimachinery/pkg/util/wait"

	"github.com/golang/glog"
	"github.com/sapcc/kubernetes-operators/sentry/pkg/apis/sentry"
	v1 "github.com/sapcc/kubernetes-operators/sentry/pkg/apis/sentry/v1"
)

func EnsureCRD(clientset apiextensionsclient.Interface) error {

	ctx := context.TODO()
	klusterCRDName := v1.SentryProjectResourcePlural + "." + sentry.GroupName
	crd := &apiextensionsv1.CustomResourceDefinition{
		ObjectMeta: metav1.ObjectMeta{
			Name: klusterCRDName,
		},
		Spec: apiextensionsv1.CustomResourceDefinitionSpec{
			Group: sentry.GroupName,
			Versions: []apiextensionsv1.CustomResourceDefinitionVersion{{
				Name:    v1.SchemeGroupVersion.Version,
				Served:  true,
				Storage: true,
				Schema: &apiextensionsv1.CustomResourceValidation{
					OpenAPIV3Schema: &apiextensionsv1.JSONSchemaProps{
						Type: "object",
						Properties: map[string]apiextensionsv1.JSONSchemaProps{
							"spec": {
								Type: "object",
								Properties: map[string]apiextensionsv1.JSONSchemaProps{
									"name": {
										Type: "string",
									},
									"team": {
										Type: "string",
									},
								}},
							"status": {
								Type: "object",
								Properties: map[string]apiextensionsv1.JSONSchemaProps{
									"state": {
										Type: "string",
									},
									"message": {
										Type: "string",
									},
								}},
						},
					},
				},
			}},
			Scope: apiextensionsv1.NamespaceScoped,
			Names: apiextensionsv1.CustomResourceDefinitionNames{
				Plural: v1.SentryProjectResourcePlural,
				Kind:   reflect.TypeOf(v1.SentryProject{}).Name(),
			},
		},
	}
	_, err := clientset.ApiextensionsV1().CustomResourceDefinitions().Create(ctx, crd, metav1.CreateOptions{})
	//TODO: Should this error if it already exit?
	if err != nil && !apierrors.IsAlreadyExists(err) {
		return err
	}
	// wait for CRD being established
	err = wait.Poll(500*time.Millisecond, 60*time.Second, func() (bool, error) {
		crd, err = clientset.ApiextensionsV1().CustomResourceDefinitions().Get(ctx, klusterCRDName, metav1.GetOptions{})
		if err != nil {
			return false, err
		}
		for _, cond := range crd.Status.Conditions {
			switch cond.Type {
			case apiextensionsv1.Established:
				if cond.Status == apiextensionsv1.ConditionTrue {
					return true, err
				}
			case apiextensionsv1.NamesAccepted:
				if cond.Status == apiextensionsv1.ConditionFalse {
					glog.Errorf("name conflict while ensuring CRD: %s", cond.Reason)
				}
			}
		}
		return false, err
	})
	if err != nil {
		deleteErr := clientset.ApiextensionsV1().CustomResourceDefinitions().Delete(ctx, klusterCRDName, metav1.DeleteOptions{})
		if deleteErr != nil {
			return apiutilerrors.NewAggregate([]error{err, deleteErr})
		}
		return err
	}
	return nil
}
