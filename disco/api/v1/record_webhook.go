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
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/webhook"

	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
	util "github.com/sapcc/kubernetes-operators/disco/pkg/util"
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

	// Ensure a FQDN for CNAME records.
	if r.Spec.Type == RecordTypeCNAME {
		r.Spec.Record = util.EnsureFQDN(r.Spec.Record)
		for idx, host := range r.Spec.Hosts {
			r.Spec.Hosts[idx] = util.EnsureFQDN(host)
		}
	}
}
