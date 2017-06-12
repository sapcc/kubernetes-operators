package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const SentryProjectResourcePlural = "sentryprojects"

type SentryProjectSpec struct {
	Name string `json:"name"`
	Team string `json:"team"`
}

type SentryProject struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata"`
	Spec              SentryProjectSpec   `json:"spec"`
	Status            SentryProjectStatus `json:"status,omitempty"`
}

type SentryProjectState string

const (
	SentryProjectPending SentryProjectState = "Pending"
	SentryProjectCreated SentryProjectState = "Created"
)

type SentryProjectStatus struct {
	State   SentryProjectState `json:"state,omitempty"`
	Message string             `json:"message,omitempty"`
}

type SentryProjectList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`
	Items           []SentryProject `json:"items"`
}
