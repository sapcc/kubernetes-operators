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

	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachineryWatch "k8s.io/apimachinery/pkg/watch"
)

func IngressHasDeletionTimestamp(ingress *extensionsv1beta1.Ingress) bool {
	return ingress.GetDeletionTimestamp() != nil
}

func isIngressNeedsUpdate(old, new *extensionsv1beta1.Ingress) bool {
	// Ingress needs update if spec or annotations changed or deletionTimestamp was added.
	if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
		return true
	}
	return false
}

func isIngressAddedOrModified(event apimachineryWatch.Event) (bool, error) {
	switch event.Type {
	case apimachineryWatch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
	case apimachineryWatch.Added, apimachineryWatch.Modified:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func isCRDAddedOrModified(event apimachineryWatch.Event) (bool, error) {
	switch event.Type {
	case apimachineryWatch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "customresourcedefinition"}, "")
	case apimachineryWatch.Added, apimachineryWatch.Modified:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func ingressHasDiscoFinalizer(ingress *extensionsv1beta1.Ingress) bool {
	for _, fin := range ingress.GetFinalizers() {
		if fin == disco.DiscoFinalizer {
			return true
		}
	}
	return false
}
