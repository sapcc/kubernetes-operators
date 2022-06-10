/*
Copyright 2022 SAP SE.

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

package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// RecordSpec defines the desired state of Record
type RecordSpec struct {
	// Type of the DNS record. Currently supported are A, CNAME, SOA, NS records.
	Type string `json:"type"`

	// List of hostnames.
	Hosts []string `json:"hosts"`

	// The record to use.
	Record string `json:"record"`

	// Optional DNS zone for the record.
	ZoneName string `json:"zoneName,omitempty"`

	// Optional description for the record.
	Description string `json:"description,omitempty"`
}

// RecordStatus defines the observed state of a Record.
type RecordStatus struct {
	// List of status conditions to indicate the status of the record.
	// +listType=map
	// +listMapKey=type
	// +optional
	Conditions []RecordCondition `json:"conditions,omitempty"`
}

type RecordCondition struct {
	// Type of the condition.
	Type RecordConditionType `json:"type"`

	// Status of the condition.
	Status metav1.ConditionStatus `json:"status"`

	// LastTransitionTime is the timestamp corresponding to the last status change of this condition.
	// +optional
	LastTransitionTime *metav1.Time `json:"lastTransitionTime,omitempty"`

	// Reason is a brief machine-readable explanation for the condition's last transition.
	// +optional
	Reason string `json:"reason,omitempty"`

	// Message is a human-readable description of the details of the last transition.
	// +optional
	Message string `json:"message,omitempty"`
}

// RecordConditionType represents a Record condition value.
type RecordConditionType string

const (
	// RecordConditionTypeReady indicates that a record is ready for use.
	RecordConditionTypeReady RecordConditionType = "Ready"
)

//+kubebuilder:object:root=true
//+kubebuilder:resource:scope=Namespaced
//+kubebuilder:subresource:status
//+kubebuilder:printcolumn:name="Record",type="string",JSONPath=".spec.record"
//+kubebuilder:printcolumn:name="Hosts",type="string",JSONPath=".spec.hosts"
//+kubebuilder:printcolumn:name="Zone",type="string",JSONPath=".spec.zoneName"
//+kubebuilder:printcolumn:name="Type",type="string",JSONPath=".spec.type"
//+kubebuilder:printcolumn:name="Ready",type="string",JSONPath=".status.conditions[?(@.type==\"Ready\")].status"

// Record is the Schema for the records API
type Record struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   RecordSpec   `json:"spec,omitempty"`
	Status RecordStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// RecordList contains a list of Record
type RecordList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Record `json:"items"`
}

func init() {
	SchemeBuilder.Register(&Record{}, &RecordList{})
}
