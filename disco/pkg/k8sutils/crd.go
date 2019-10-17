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
	crdutils "github.com/ant31/crd-validation/pkg"
	discoCRD "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco"
	discoV1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco/v1"
	extensionsobj "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1beta1"
)

// NewDiscoRecordCRD returns a new Record custom resource definition.
func NewDiscoRecordCRD() *extensionsobj.CustomResourceDefinition {
	crd := crdutils.NewCustomResourceDefinition(crdutils.Config{
		SpecDefinitionName:    "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco/v1.Record",
		EnableValidation:      true,
		ResourceScope:         string(extensionsobj.NamespaceScoped),
		Group:                 discoCRD.GroupName,
		Kind:                  discoV1.RecordKind,
		Version:               discoV1.Version,
		Plural:                discoV1.RecordKindPlural,
		GetOpenAPIDefinitions: discoV1.GetOpenAPIDefinitions,
	})
	crd.Spec.AdditionalPrinterColumns = []extensionsobj.CustomResourceColumnDefinition{
		{
			Name: "record",
			Type: "string",
			Description: "The record",
			JSONPath: ".spec.record",
		},
		{
			Name: "type",
			Type: "string",
			Description: "The type of the record",
			JSONPath: ".spec.type",
		},
	}
	crd.Spec.Subresources = nil
	return crd
}
