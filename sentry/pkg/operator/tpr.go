package operator

import (
	"time"

	tprv1 "github.com/sapcc/kubernetes-operators/sentry/pkg/tpr/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	apiv1 "k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/rest"
)

func CreateTPR(clientset kubernetes.Interface) error {
	tpr := &v1beta1.ThirdPartyResource{
		ObjectMeta: metav1.ObjectMeta{
			Name: "sentry-project." + tprv1.GroupName,
		},
		Versions: []v1beta1.APIVersion{
			{Name: tprv1.SchemeGroupVersion.Version},
		},
		Description: "Provision sentry projects",
	}
	_, err := clientset.ExtensionsV1beta1().ThirdPartyResources().Create(tpr)
	return err
}

func WaitForSentyProjectResource(client *rest.RESTClient) error {
	return wait.Poll(100*time.Millisecond, 60*time.Second, func() (bool, error) {
		_, err := client.Get().Namespace(apiv1.NamespaceDefault).Resource(tprv1.SentryProjectResourcePlural).DoRaw()
		if err == nil {
			return true, nil
		}
		if apierrors.IsNotFound(err) {
			return false, nil
		}
		return false, err
	})
}
