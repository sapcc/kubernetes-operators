package v1

import (
	"errors"
	"regexp"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const SentryProjectResourcePlural = "sentryprojects"

var isSlug = regexp.MustCompile(`^[-a-z0-9]+$`).MatchString

// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
type SentryProject struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata"`
	Spec              SentryProjectSpec   `json:"spec"`
	Status            SentryProjectStatus `json:"status,omitempty"`
}

type SentryProjectSpec struct {
	Name string `json:"name"`
	Team string `json:"team"`
}

func (spec SentryProjectSpec) Validate() error {
	if !isSlug(spec.Name) {
		return errors.New("Project name is not a valid slug. Only letters, numbers or hyphens are allowed")
	}
	if !isSlug(spec.Team) {
		return errors.New("Team name is not a valid slug. Only letters, numbers or hyphens are allowed")
	}
	return nil
}

type SentryProjectState string

const (
	SentryProjectPending   SentryProjectState = "Pending"
	SentryProjectProcessed SentryProjectState = "Processed"
	SentryProjectError     SentryProjectState = "Error"
)

type SentryProjectStatus struct {
	State   SentryProjectState `json:"state,omitempty"`
	Message string             `json:"message,omitempty"`
}

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
type SentryProjectList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`
	Items           []SentryProject `json:"items"`
}
