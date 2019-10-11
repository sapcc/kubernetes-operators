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

package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const (
	// Version of the CRDs.
	Version = "v1"

	// RecordKind ...
	RecordKind = "Record"
	// RecordKindPlural ...
	RecordKindPlural = "records"
)

// Record is a specification for a Record resource
// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +k8s:openapi-gen=true
type Record struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	// Specification of the Record.
	Spec RecordSpec `json:"spec"`
}

// RecordSpec is the spec for a Record resource
// +k8s:openapi-gen=true
type RecordSpec struct {
	// Type of the DNS record.
	// Currently supported are A, CNAME, SOA, NS records.
	Type string `json:"type"`
	// List of hostnames.
	Hosts []string `json:"hosts"`
	// The record to use.
	Record string `json:"record"`
	// Optional zone for the record.
	ZoneName string `json:"zoneName,omitempty"`
	// Optional description for the record.
	Description string `json:"description,omitempty"`
}

// RecordList is a list of Record resources
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +k8s:openapi-gen=true
type RecordList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`

	// List of Records.
	Items []Record `json:"items"`
}
