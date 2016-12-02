package example

import (
	"encoding/json"

	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/pkg/api"
	"k8s.io/client-go/1.5/pkg/api/meta"
	"k8s.io/client-go/1.5/pkg/api/unversioned"
	"k8s.io/client-go/1.5/pkg/api/v1"
	"k8s.io/client-go/1.5/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/1.5/pkg/runtime"
	"k8s.io/client-go/1.5/pkg/runtime/serializer"
	"k8s.io/client-go/1.5/rest"
)

type CritterSpec struct {
	Owner string `json:"owner"`
	Color string `json:"color"`
}

type Critter struct {
	unversioned.TypeMeta `json:",inline"`
	Metadata             api.ObjectMeta `json:"metadata"`

	Spec CritterSpec `json:"spec"`
}

type CritterList struct {
	unversioned.TypeMeta `json:",inline"`
	Metadata             unversioned.ListMeta `json:"metadata"`

	Items []Critter `json:"items"`
}

func NewCritterClientForConfig(c *rest.Config) (*rest.RESTClient, error) {
	c.APIPath = "/apis"
	c.GroupVersion = &unversioned.GroupVersion{
		Group:   "stable.sap.cc",
		Version: "v1",
	}
	c.NegotiatedSerializer = serializer.DirectCodecFactory{CodecFactory: api.Codecs}

	schemeBuilder := runtime.NewSchemeBuilder(
		func(scheme *runtime.Scheme) error {
			scheme.AddKnownTypes(
				*c.GroupVersion,
				&Critter{},
				&CritterList{},
				&api.ListOptions{},
				&api.DeleteOptions{},
			)
			return nil
		})
	schemeBuilder.AddToScheme(api.Scheme)

	return rest.RESTClientFor(c)
}

func EnsureCritterThirdPartyResource(client *kubernetes.Clientset) error {
	_, err := client.Extensions().ThirdPartyResources().Get("critter.stable.sap.cc")
	if err != nil {
		// The resource doesn't exist, so we create it.
		newResource := v1beta1.ThirdPartyResource{
			ObjectMeta: v1.ObjectMeta{
				Name: "critter.stable.sap.cc",
			},
			Description: "A specification of a small furry animal",
			Versions: []v1beta1.APIVersion{
				{Name: "v1"},
			},
		}

		_, err = client.Extensions().ThirdPartyResources().Create(&newResource)
	}

	return err
}

// The code below is used only to work around a known problem with third-party
// resources and ugorji. If/when these issues are resolved, the code below
// should no longer be required.
//

func (c *Critter) GetObjectKind() unversioned.ObjectKind {
	return &c.TypeMeta
}

func (c *Critter) GetObjectMeta() meta.Object {
	return &c.Metadata
}

func (cl *CritterList) GetObjectKind() unversioned.ObjectKind {
	return &cl.TypeMeta
}

func (cl *CritterList) GetListMeta() unversioned.List {
	return &cl.Metadata
}

type CritterListCopy CritterList
type CritterCopy Critter

func (e *Critter) UnmarshalJSON(data []byte) error {
	tmp := CritterCopy{}
	err := json.Unmarshal(data, &tmp)
	if err != nil {
		return err
	}
	tmp2 := Critter(tmp)
	*e = tmp2
	return nil
}

func (el *CritterList) UnmarshalJSON(data []byte) error {
	tmp := CritterListCopy{}
	err := json.Unmarshal(data, &tmp)
	if err != nil {
		return err
	}
	tmp2 := CritterList(tmp)
	*el = tmp2
	return nil
}
