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

	"github.com/go-logr/logr"
	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/handler"
	"sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/source"

	discov1 "github.com/sapcc/kubernetes-operators/disco/api/v1"
	"github.com/sapcc/kubernetes-operators/disco/pkg/clientutil"
	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
)

// ServiceShimReconciler reconciles a service object
type ServiceShimReconciler struct {
	AnnotationKey string
	logger        logr.Logger
	c             client.Client
	scheme        *runtime.Scheme
}

//+kubebuilder:rbac:groups="",resources=service,verbs=get;list;watch
//+kubebuilder:rbac:groups=disco.stable.sap.cc,resources=records,verbs=get;list;watch;create;update;patch;delete

// SetupWithManager sets up the controller with the Manager.
func (r *ServiceShimReconciler) SetupWithManager(mgr ctrl.Manager) error {
	if r.AnnotationKey == "" {
		return errors.New("annotation for service resources not provided")
	}

	r.c = mgr.GetClient()
	r.scheme = mgr.GetScheme()

	name := "service-shim"
	r.logger = mgr.GetLogger().WithName(name)
	return ctrl.NewControllerManagedBy(mgr).
		Named(name).
		For(&corev1.Service{}).
		Watches(&source.Kind{Type: &discov1.Record{}}, &handler.EnqueueRequestForOwner{OwnerType: &corev1.Service{}}).
		WithOptions(controller.Options{Log: r.logger, MaxConcurrentReconciles: 1}).
		Complete(r)
}

func (r *ServiceShimReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	ctx = log.IntoContext(ctx, r.logger.WithValues("service", req.NamespacedName.String()))

	var svc = new(corev1.Service)
	if err := r.c.Get(ctx, req.NamespacedName, svc); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !isHandleObject(r.AnnotationKey, svc) {
		log.FromContext(ctx).V(5).Info("ignoring service with missing annotation",
			"annotation", r.AnnotationKey)
		return ctrl.Result{}, nil
	}

	// TODO: This is confusing as the record is the IP and the host is specified via annotation.
	// In case of services specify AnnotationHosts or similar.
	rec, ok := r.getAnnotationValue(disco.AnnotationRecord, svc)
	if !ok {
		log.FromContext(ctx).Info("ignoring service with missing annotation",
			"annotation", makeAnnotation(r.AnnotationKey, disco.AnnotationRecord))
		return ctrl.Result{}, nil
	}

	recordsetType := "A"
	if v, ok := r.getAnnotationValue(disco.AnnotationRecordType, svc); ok {
		recordsetType = v
	}

	ipList := make([]string, 0)
	if lbIP := svc.Spec.LoadBalancerIP; lbIP != "" {
		ipList = appendIfNotContains(ipList, lbIP)
	}
	if extIPList := svc.Spec.ExternalIPs; extIPList != nil {
		for _, extIP := range extIPList {
			ipList = appendIfNotContains(ipList, extIP)
		}
	}
	if ingEPList := svc.Status.LoadBalancer.Ingress; ingEPList != nil {
		for _, ingEP := range ingEPList {
			ipList = appendIfNotContains(ipList, ingEP.IP)
		}
	}

	for _, ip := range ipList {
		var record = new(discov1.Record)
		record.Name = fmt.Sprintf("%s-%s", svc.Name, ip)
		record.Namespace = svc.Namespace

		result, err := clientutil.CreateOrPatch(ctx, r.c, record, func() error {
			record.Spec.Record = ip
			record.Spec.Type = recordsetType
			record.Spec.Hosts = []string{rec}
			record.Spec.Description = fmt.Sprintf("Created for svc %s/%s.", svc.Namespace, svc.Name)
			if v, ok := r.getAnnotationValue(disco.AnnotationRecordZoneName, svc); ok {
				record.Spec.ZoneName = v
			}
			return controllerutil.SetOwnerReference(svc, record, r.scheme)
		})
		if err != nil {
			return ctrl.Result{}, err
		}
		switch result {
		case clientutil.OperationResultCreated:
			log.FromContext(ctx).Info("created record", "namespace", record.Namespace, "name", record.Name)
		case clientutil.OperationResultUpdated:
			log.FromContext(ctx).Info("updated record", "namespace", record.Namespace, "name", record.Name)
		}
	}
	return ctrl.Result{}, nil
}

func (r *ServiceShimReconciler) getAnnotationValue(key string, svc *corev1.Service) (string, bool) {
	if svc.GetAnnotations() == nil {
		return "", false
	}
	v, ok := svc.Annotations[makeAnnotation(r.AnnotationKey, key)]
	return v, ok
}
