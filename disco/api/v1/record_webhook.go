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
	"k8s.io/apimachinery/pkg/runtime"
	utilerrors "k8s.io/apimachinery/pkg/util/errors"
	"k8s.io/apimachinery/pkg/util/validation/field"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/webhook"

	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
)

func (r *Record) SetupWebhookWithManager(mgr ctrl.Manager) error {
	return ctrl.NewWebhookManagedBy(mgr).
		For(r).
		Complete()
}

//+kubebuilder:webhook:path=/mutate-disco-stable-sap-cc-v1-record,mutating=true,failurePolicy=fail,sideEffects=None,groups=disco.stable.sap.cc,resources=records,verbs=create;update,versions=v1,name=mrecord.kb.io,admissionReviewVersions=v1

var _ webhook.Defaulter = &Record{}

// Default implements webhook.Defaulter so a webhook will be registered for the type
func (r *Record) Default() {
	if r.Spec.ZoneName == "" {
		r.Spec.ZoneName = disco.DefaultDNSZoneName
	}
}

//+kubebuilder:webhook:path=/validate-disco-stable-sap-cc-v1-record,mutating=false,failurePolicy=fail,sideEffects=None,groups=disco.stable.sap.cc,resources=records,verbs=create;update,versions=v1,name=vrecord.kb.io,admissionReviewVersions=v1

var _ webhook.Validator = &Record{}

// ValidateCreate implements webhook.Validator so a webhook will be registered for the type
func (r *Record) ValidateCreate() error {
	var allErrs []error
	if err := isSupportedRecordTypeOrError(r.Spec.Type); err != nil {
		allErrs = append(allErrs, err)
	}
	if len(allErrs) > 0 {
		return utilerrors.NewAggregate(allErrs)
	}
	return nil
}

// ValidateUpdate implements webhook.Validator so a webhook will be registered for the type
func (r *Record) ValidateUpdate(_ runtime.Object) error {
	var allErrs []error
	if err := isSupportedRecordTypeOrError(r.Spec.Type); err != nil {
		allErrs = append(allErrs, err)
	}
	if len(allErrs) > 0 {
		return utilerrors.NewAggregate(allErrs)
	}
	return nil
}

// ValidateDelete implements webhook.Validator so a webhook will be registered for the type
func (r *Record) ValidateDelete() error {
	return nil
}

func isSupportedRecordTypeOrError(recordType string) error {
	supportedRecordTypes := []string{"CNAME", "A", "SOA", ""}
	if !isStringSliceContains(supportedRecordTypes, recordType) {
		return field.NotSupported(field.NewPath("spec").Child("type"), recordType, supportedRecordTypes)
	}
	return nil
}

func isStringSliceContains(theStringSlice []string, theString string) bool {
	for _, s := range theStringSlice {
		if s == theString {
			return true
		}
	}
	return false
}
