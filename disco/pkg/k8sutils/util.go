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

	v1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco/v1"
	coreV1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachineryWatch "k8s.io/apimachinery/pkg/watch"
)

// HasDeletionTimestamp checks whether an attempt was made to delete the object and thus a deletion timestamp is set.
func HasDeletionTimestamp(obj runtime.Object) bool {
	objMeta, err := meta.Accessor(obj)
	if err != nil {
		return false
	}
	return objMeta.GetDeletionTimestamp() != nil
}

func isIngressNeedsUpdate(old, new *extensionsv1beta1.Ingress) bool {
	// Ingress needs update if spec or annotations changed or deletionTimestamp was added.
	if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
		return true
	}
	return false
}

func isServiceNeedsUpdate(old, new *coreV1.Service) bool {
	// Service needs update if spec or annotations changed or deletionTimestamp was added.
	if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
		return true
	}
	return false
}

func isDiscoRecordNeedsUpdate(old, new *v1.Record) bool {
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
	}
	return false, nil
}

func isServiceAddedOrModified(event apimachineryWatch.Event) (bool, error) {
	switch event.Type {
	case apimachineryWatch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "service"}, "")
	case apimachineryWatch.Added, apimachineryWatch.Modified:
		return true, nil
	}
	return false, nil
}

func isDiscoRecordAddedOrModified(event apimachineryWatch.Event) (bool, error) {
	switch event.Type {
	case apimachineryWatch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "discoRecord"}, "")
	case apimachineryWatch.Added, apimachineryWatch.Modified:
		return true, nil
	}
	return false, nil
}

func isCRDAddedOrModified(event apimachineryWatch.Event) (bool, error) {
	switch event.Type {
	case apimachineryWatch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "customresourcedefinition"}, "")
	case apimachineryWatch.Added, apimachineryWatch.Modified:
		return true, nil
	}
	return false, nil
}

func hasDiscoFinalizer(obj runtime.Object, finalizer string) bool {
	objMeta, err := meta.Accessor(obj)
	if err != nil {
		return false
	}

	for _, fin := range objMeta.GetFinalizers() {
		if fin == finalizer {
			return true
		}
	}
	return false
}
