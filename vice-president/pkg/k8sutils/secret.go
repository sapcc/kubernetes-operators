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
	coreV1 "k8s.io/api/core/v1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
	"reflect"
)

func newEmptySecret(nameSpace, name string, labels, annotations map[string]string) *coreV1.Secret {
	if labels == nil {
		labels = map[string]string{}
	}
	if annotations == nil {
		annotations = map[string]string{}
	}
	return &coreV1.Secret{
		Type: coreV1.SecretTypeOpaque,
		ObjectMeta: metaV1.ObjectMeta{
			Name:        name,
			Namespace:   nameSpace,
			Labels:      labels,
			Annotations: annotations,
		},
		Data: map[string][]byte{},
	}
}

func secretHasAnnotation(secret *coreV1.Secret, annotation string) bool {
	_, ok := secret.GetAnnotations()[annotation]
	return ok
}

func isSecretAddedOrModified(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "secret"}, "")
	case watch.Added, watch.Modified:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func isSecretDeleted(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func isSecretNeedsUpdate(old, new *coreV1.Secret) bool {
	if !reflect.DeepEqual(old.Data, new.Data) || !reflect.DeepEqual(old.Annotations, new.Annotations) {
		return true
	}
	return false
}
