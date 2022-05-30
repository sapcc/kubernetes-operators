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
package controller

import (
	"context"
	"reflect"
	"time"

	seederv1 "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/apis/seeder/v1"

	"github.com/golang/glog"
	"github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/apis/seeder"
	apiextensionsv1 "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/errors"
	"k8s.io/apimachinery/pkg/util/wait"
)

const openstackseedCRDName = seederv1.OpenstackSeedResourcePlural + "." + seeder.GroupName

func CreateCustomResourceDefinition(clientset apiextensionsclient.Interface) (*apiextensionsv1.CustomResourceDefinition, error) {
	glog.Infof("Checking CustomResourceDefinition %s", openstackseedCRDName)

	//validation := crdvalidation.GetCustomResourceValidation("github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/apis/seeder/v1.OpenstackSeed", seederv1.GetOpenAPIDefinitions)
	version := apiextensionsv1.CustomResourceDefinitionVersion{
		Name:    seederv1.SchemeGroupVersion.Version,
		Storage: true,
		//Schema: validation,
	}

	crd := &apiextensionsv1.CustomResourceDefinition{
		ObjectMeta: metav1.ObjectMeta{
			Name: openstackseedCRDName,
		},
		Spec: apiextensionsv1.CustomResourceDefinitionSpec{
			Group:    seeder.GroupName,
			Versions: []apiextensionsv1.CustomResourceDefinitionVersion{version},
			Scope:    apiextensionsv1.NamespaceScoped,
			Names: apiextensionsv1.CustomResourceDefinitionNames{
				Plural: seederv1.OpenstackSeedResourcePlural,
				Kind:   reflect.TypeOf(seederv1.OpenstackSeed{}).Name(),
			},
		},
	}

	_, err := clientset.ApiextensionsV1().CustomResourceDefinitions().Create(context.TODO(), crd, metav1.CreateOptions{})
	if err != nil {
		if apierrors.IsAlreadyExists(err) {
			// check if the (new) CRD validation has been put in place yet
			crd, err = clientset.ApiextensionsV1().CustomResourceDefinitions().Get(context.TODO(), openstackseedCRDName, metav1.GetOptions{})
			if err != nil {
				glog.Errorf("Get CustomResourceDefinition %s failed: %v", openstackseedCRDName, err)
				return nil, err
			}
			glog.Infof("Updating validation for CustomResourceDefinition %s", openstackseedCRDName)
			crd.Spec.Versions = []apiextensionsv1.CustomResourceDefinitionVersion{version}
			crd, err = clientset.ApiextensionsV1().CustomResourceDefinitions().Update(context.TODO(), crd, metav1.UpdateOptions{})
			if err != nil {
				glog.Errorf("Validation update of CustomResourceDefinition %s failed: %v", openstackseedCRDName, err)
				return nil, err
			}
			return crd, nil
		}
		glog.Errorf("Create CustomResourceDefinition %s failed: %v", openstackseedCRDName, err)
		return nil, err
	}

	// wait for CRD being established
	glog.Info("Waiting for CustomResourceDefinition")
	err = wait.Poll(500*time.Millisecond, 60*time.Second, func() (bool, error) {
		crd, err = clientset.ApiextensionsV1().CustomResourceDefinitions().Get(context.TODO(), openstackseedCRDName, metav1.GetOptions{})
		if err != nil {
			glog.Errorf("Wait for CustomResourceDefinition failed %v", err)
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
					glog.Errorf("Name conflict: %v", cond.Reason)
				}
			}
		}
		return false, err
	})
	if err != nil {
		glog.Warningf("Deleting CustomResourceDefinition %s due to %v", openstackseedCRDName, err)
		deleteErr := clientset.ApiextensionsV1beta1().CustomResourceDefinitions().Delete(context.TODO(), openstackseedCRDName, metav1.DeleteOptions{})
		if deleteErr != nil {
			return nil, errors.NewAggregate([]error{err, deleteErr})
		}
		return nil, err
	}

	glog.Infof("CustomResourceDefinition %s created", openstackseedCRDName)

	return crd, nil
}
