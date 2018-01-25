/*
Copyright 2017 SAP SE

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package client

import (
	"reflect"
	"time"

	seederv1 "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/apis/v1"

	apiextensionsv1beta1 "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1beta1"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/errors"
	"k8s.io/apimachinery/pkg/util/wait"
	// Uncomment the following line to load the gcp plugin (only required to authenticate against GKE clusters).
	// _ "k8s.io/client-go/plugin/pkg/client/auth/gcp"
	"github.com/golang/glog"
)

const openstackseedCRDName = seederv1.OpenstackSeedResourcePlural + "." + seederv1.GroupName

func CreateCustomResourceDefinition(clientset apiextensionsclient.Interface) (*apiextensionsv1beta1.CustomResourceDefinition, error) {
	crd := &apiextensionsv1beta1.CustomResourceDefinition{
		ObjectMeta: metav1.ObjectMeta{
			Name: openstackseedCRDName,
		},
		Spec: apiextensionsv1beta1.CustomResourceDefinitionSpec{
			Group:   seederv1.GroupName,
			Version: seederv1.SchemeGroupVersion.Version,
			Scope:   apiextensionsv1beta1.NamespaceScoped,
			Names: apiextensionsv1beta1.CustomResourceDefinitionNames{
				Plural: seederv1.OpenstackSeedResourcePlural,
				Kind:   reflect.TypeOf(seederv1.OpenstackSeed{}).Name(),
			},
		},
	}
	glog.Infof("Creating CustomResourceDefinition %s", openstackseedCRDName)

	_, err := clientset.ApiextensionsV1beta1().CustomResourceDefinitions().Create(crd)
	if err != nil {
		glog.Errorf("Create CustomResourceDefinition %s failed: %v", openstackseedCRDName, err)
		return nil, err
	}

	// wait for CRD being established
	glog.Info("Waiting for CustomResourceDefinition")
	err = wait.Poll(500*time.Millisecond, 60*time.Second, func() (bool, error) {
		crd, err = clientset.ApiextensionsV1beta1().CustomResourceDefinitions().Get(openstackseedCRDName, metav1.GetOptions{})
		if err != nil {
			glog.Errorf("Wait for CustomResourceDefinition failed %v", err)
			return false, err
		}
		for _, cond := range crd.Status.Conditions {
			switch cond.Type {
			case apiextensionsv1beta1.Established:
				if cond.Status == apiextensionsv1beta1.ConditionTrue {
					return true, err
				}
			case apiextensionsv1beta1.NamesAccepted:
				if cond.Status == apiextensionsv1beta1.ConditionFalse {
					glog.Errorf("Name conflict: %v", cond.Reason)
				}
			}
		}
		return false, err
	})
	if err != nil {
		glog.Warningf("Deleting CustomResourceDefinition %s due to %v", openstackseedCRDName, err)
		deleteErr := clientset.ApiextensionsV1beta1().CustomResourceDefinitions().Delete(openstackseedCRDName, nil)
		if deleteErr != nil {
			return nil, errors.NewAggregate([]error{err, deleteErr})
		}
		return nil, err
	}
	glog.Infof("CustomResourceDefinition %s created", openstackseedCRDName)
	return crd, nil
}
