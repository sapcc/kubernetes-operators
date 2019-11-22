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

package controller

import (
	"errors"
	"strings"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/meta"
)

// The providerID contains the serverID and looks like:
// openstack:///352378e0-7610-45c4-bfb4-9ad973ef8652
const providerPrefix = "openstack:///"

func getServerIDFromNode(node *corev1.Node) (string, error) {
	providerStr := node.Spec.ProviderID
	if serverID := strings.TrimLeft(providerStr, providerPrefix); serverID != "" {
		return serverID, nil
	}
	return "", errors.New("serverID not found in provider ID")
}

func getAnnotationValue(obj interface{}, lblKey string) (string, bool) {
	objMeta, err := meta.Accessor(obj)
	if err != nil {
		return "", false
	}

	ann := objMeta.GetAnnotations()
	if ann == nil {
		return "", false
	}

	val, ok := ann[lblKey]
	return val, ok
}

func getLabelValue(obj interface{}, lblKey string) (string, bool) {
	objMeta, err := meta.Accessor(obj)
	if err != nil {
		return "", false
	}

	lbl := objMeta.GetLabels()
	if lbl == nil {
		return "", false
	}

	val, ok := lbl[lblKey]
	return val, ok
}
