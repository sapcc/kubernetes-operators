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

package controllers

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/go-logr/logr"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
	"github.com/pkg/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/utils/strings/slices"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	discov1 "github.com/sapcc/kubernetes-operators/disco/api/v1"
	"github.com/sapcc/kubernetes-operators/disco/pkg/clientutil"
	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
)

const (
	finalizerDisco   = "disco.extensions/v1beta1"
	defaultRecordTTL = 1800
)

// RecordReconciler reconciles a Record object
type RecordReconciler struct {
	ReconciliationInterval time.Duration
	logger                 logr.Logger
	c                      client.Client
	scheme                 *runtime.Scheme
	dnsV2Client            *disco.DNSV2Client
}

//+kubebuilder:rbac:groups=disco.stable.sap.cc,resources=records,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=disco.stable.sap.cc,resources=records/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=disco.stable.sap.cc,resources=records/finalizers,verbs=update

// SetupWithManager sets up the controller with the Manager.
func (r *RecordReconciler) SetupWithManager(mgr ctrl.Manager) error {
	if r.ReconciliationInterval == 0 {
		return errors.New("reconciliation interval must not be 0")
	}

	dnsV2Client, err := disco.NewDNSV2ClientFromENV()
	if err != nil {
		return err
	}
	r.dnsV2Client = dnsV2Client
	r.c = mgr.GetClient()
	r.scheme = mgr.GetScheme()

	name := "disco"
	r.logger = mgr.GetLogger().WithName(name)
	return ctrl.NewControllerManagedBy(mgr).
		Named(name).
		For(&discov1.Record{}).
		WithOptions(controller.Options{Log: r.logger, MaxConcurrentReconciles: 1}).
		Complete(r)
}

func (r *RecordReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	ctx = log.IntoContext(ctx, r.logger.WithValues("record", req.NamespacedName.String()))

	var record = new(discov1.Record)
	if err := r.c.Get(ctx, req.NamespacedName, record); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Cleanup logic for recordset being deleted.
	if record.DeletionTimestamp != nil && controllerutil.ContainsFinalizer(record, finalizerDisco) {
		log.FromContext(ctx).Info("cleaning up record being deleted", "deletionTimestamp", record.DeletionTimestamp.String())
		if err := r.cleanupRecordset(ctx, record); err != nil {
			return ctrl.Result{}, err
		}
		err := r.removeFinalizer(ctx, record, finalizerDisco)
		return ctrl.Result{}, err
	}

	if err := r.ensureFinalizer(ctx, record, finalizerDisco); err != nil {
		return ctrl.Result{}, err
	}

	if err := r.reconcileRecord(ctx, record); err != nil {
		return ctrl.Result{}, err
	}

	if err := r.reconcileStatus(ctx, record); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{RequeueAfter: r.ReconciliationInterval}, nil
}

func (r *RecordReconciler) ensureFinalizer(ctx context.Context, record *discov1.Record, finalizer string) error {
	_, err := clientutil.CreateOrPatch(ctx, r.c, record, func() error {
		controllerutil.AddFinalizer(record, finalizer)
		return nil
	})
	return err
}

func (r *RecordReconciler) removeFinalizer(ctx context.Context, record *discov1.Record, finalizer string) error {
	_, err := clientutil.Patch(ctx, r.c, record, func() error {
		controllerutil.RemoveFinalizer(record, finalizer)
		return nil
	})
	return err
}

func (r *RecordReconciler) reconcileRecord(ctx context.Context, record *discov1.Record) error {
	zone, err := r.dnsV2Client.GetZoneByName(ctx, record.Spec.ZoneName)
	if err != nil {
		return err
	}

	records := strings.FieldsFunc(ensureFQDN(record.Spec.Record), splitFunc)
	if rec := records; len(rec) > 0 {
		records = rec
	}

	for _, host := range record.Spec.Hosts {
		recordset, isFound, err := r.dnsV2Client.GetRecordsetByZoneAndName(ctx, zone.ID, host)
		if err != nil {
			return err
		}

		// Create the recordset if it cannot be found.
		if !isFound {
			log.FromContext(ctx).Info("record does not exist in designate. creating it",
				"zone", zone.Name, "name", host, "type", record.Spec.Type, "records", records[0], "ttl", defaultRecordTTL)
			err := r.dnsV2Client.CreateRecordset(ctx, zone.ID, host, record.Spec.Type, record.Spec.Description, records, defaultRecordTTL)
			return err
		}

		// The recordset exists but needs updating.
		if !isDesignateRecordsetEqualToRecord(recordset, record) {
			log.FromContext(ctx).Info("updating record in designate",
				"zone", zone.Name, "name", host, "type", record.Spec.Type, "records", records[0], "ttl", defaultRecordTTL)
			err := r.dnsV2Client.UpdateRecordset(recordset.ZoneID, recordset.ID, record.Spec.Description, defaultRecordTTL, record.Spec.Hosts)
			return err
		}

	}

	return nil
}

func (r *RecordReconciler) reconcileStatus(ctx context.Context, record *discov1.Record) error {
	readyCondition := r.getReadyConditionForRecord(ctx, record)
	_, err := clientutil.PatchStatus(ctx, r.c, record, func() error {
		if record.Status.Conditions == nil {
			record.Status.Conditions = make([]discov1.RecordCondition, 0)
		}
		record.Status.Conditions = setCondition(record.Status.Conditions, readyCondition)
		return nil
	})
	return err
}

func (r *RecordReconciler) cleanupRecordset(ctx context.Context, record *discov1.Record) error {
	zone, err := r.dnsV2Client.GetZoneByName(ctx, record.Spec.ZoneName)
	if err != nil {
		return err
	}
	for _, host := range record.Spec.Hosts {
		if err := r.dnsV2Client.DeleteRecordsetByZoneAndNameIgnoreNotFound(ctx, zone.ID, host); err != nil {
			return err
		}
	}
	return nil
}

func (r *RecordReconciler) getReadyConditionForRecord(ctx context.Context, record *discov1.Record) *discov1.RecordCondition {
	now := metav1.Now()
	readyCondition := &discov1.RecordCondition{
		Type:               discov1.RecordConditionTypeReady,
		Status:             metav1.ConditionUnknown,
		LastTransitionTime: &now,
		Reason:             "",
		Message:            "",
	}

	zone, err := r.dnsV2Client.GetZoneByName(ctx, record.Spec.ZoneName)
	if err != nil {
		readyCondition.Status = metav1.ConditionFalse
		readyCondition.Reason = "failed to get dns zone"
		readyCondition.Message = err.Error()
		return readyCondition
	}

	recordset, isFound, err := r.dnsV2Client.GetRecordsetByZoneAndName(ctx, zone.ID, record.Spec.Record)
	if err != nil {
		readyCondition.Status = metav1.ConditionFalse
		readyCondition.Reason = "failed to get recordset"
		readyCondition.Message = err.Error()
		return readyCondition
	}
	if !isFound {
		readyCondition.Status = metav1.ConditionFalse
		readyCondition.Reason = "not found in designate"
		return readyCondition
	}
	readyCondition.Status = metav1.ConditionTrue
	readyCondition.Reason = "recordset is ready"
	readyCondition.Message = fmt.Sprintf("recordset is in status %s", recordset.Status)
	return readyCondition
}

func setCondition(curConditions []discov1.RecordCondition, conditionToSet *discov1.RecordCondition) []discov1.RecordCondition {
	for idx, c := range curConditions {
		if c.Type == conditionToSet.Type {
			curConditions[idx].Reason = conditionToSet.Reason
			curConditions[idx].Message = conditionToSet.Message
			// Carry over last transition timestamp if status changed.
			if curConditions[idx].Status != conditionToSet.Status {
				curConditions[idx].Status = conditionToSet.Status
				curConditions[idx].LastTransitionTime = conditionToSet.LastTransitionTime
			}
			return curConditions
		}
	}
	return curConditions
}

func isDesignateRecordsetEqualToRecord(designateRecordset recordsets.RecordSet, record *discov1.Record) bool {
	return designateRecordset.Name == record.Spec.Record &&
		designateRecordset.Type == record.Spec.Type &&
		isStringSlicesEqual(designateRecordset.Records, record.Spec.Hosts)
}

func isStringSlicesEqual(a, b []string) bool {
	sort.Strings(a)
	sort.Strings(b)
	return slices.Equal(a, b)
}
