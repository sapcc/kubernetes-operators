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

package disco

import (
	"fmt"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/gophercloud/gophercloud/openstack/dns/v2/zones"
	expiringCache "github.com/patrickmn/go-cache"
	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus"
	discoV1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco/v1"
	"github.com/sapcc/kubernetes-operators/disco/pkg/config"
	"github.com/sapcc/kubernetes-operators/disco/pkg/k8sutils"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
	"github.com/sapcc/kubernetes-operators/disco/pkg/metrics"
	"github.com/sapcc/kubernetes-operators/disco/pkg/version"
	v1 "k8s.io/api/core/v1"
	"k8s.io/api/extensions/v1beta1"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/util/workqueue"
)

// Operator is the CNAME operator (disco).
type Operator struct {
	config.Options
	*config.Config

	logger          log.Logger
	dnsV2Client     *DNSV2Client
	k8sFramework    *k8sutils.K8sFramework
	ResyncPeriod    time.Duration
	RecheckInterval time.Duration
	queue           workqueue.RateLimitingInterface
	zoneCache       *expiringCache.Cache
}

// New creates a new operator using the given options
func New(options config.Options, logger log.Logger) (*Operator, error) {
	if err := options.CheckOptions(logger); err != nil {
		return nil, err
	}

	discoConfig, err := config.ReadConfig(options.ConfigPath)
	if err != nil {
		return nil, err
	}

	k8sFramwork, err := k8sutils.NewK8sFramework(options, logger)
	if err != nil {
		return nil, err
	}

	dnsV2Client, err := NewDNSV2ClientFromAuthOpts(discoConfig.AuthOpts, logger)
	if err != nil {
		return nil, err
	}

	operator := &Operator{
		Options:         options,
		k8sFramework:    k8sFramwork,
		dnsV2Client:     dnsV2Client,
		Config:          discoConfig,
		ResyncPeriod:    options.ResyncPeriod,
		RecheckInterval: options.RecheckPeriod,
		queue:           workqueue.NewRateLimitingQueue(workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second)),
		logger:          log.NewLoggerWith(logger, "component", "operator"),
		zoneCache:       expiringCache.New(options.RecheckPeriod, 2*options.RecheckPeriod),
	}

	operator.k8sFramework.AddIngressInformerEventHandler(
		operator.enqueueItem,
		operator.enqueueItem,
		func(oldObj, newObj interface{}) {
			old := oldObj.(*v1beta1.Ingress)
			new := newObj.(*v1beta1.Ingress)
			// Enqueue if either Spec, annotations changed or DeletionTimestamp was set.
			if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
				operator.enqueueItem(newObj)
			}
		},
	)

	operator.k8sFramework.AddServiceInformerEventHandler(
		operator.enqueueItem,
		operator.enqueueItem,
		func(oldObj, newObj interface{}) {
			old := oldObj.(*v1.Service)
			new := newObj.(*v1.Service)
			// Enqueue if either Spec, annotations changed or DeletionTimestamp was set.
			if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
				operator.enqueueItem(newObj)
			}
		},
	)

	operator.k8sFramework.AddDiscoCRDInformerEventHandler(
		operator.enqueueItem,
		operator.enqueueItem,
		func(oldObj, newObj interface{}) {
			old := oldObj.(*discoV1.Record)
			new := newObj.(*discoV1.Record)
			// Enqueue if either Spec changed or DeletionTimestamp was set.
			if !reflect.DeepEqual(old.Spec, new.Spec) || !reflect.DeepEqual(old.GetDeletionTimestamp(), new.GetDeletionTimestamp()) {
				operator.enqueueItem(newObj)
			}
		},
	)

	return operator, nil
}

// Run starts the operator
func (disco *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer utilruntime.HandleCrash()
	defer disco.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)

	disco.logger.LogInfo("Ladies and Gentlemen, the DISCO is about to begin! Creating your OpenStack Designate records now.", "version", version.Version)

	if disco.IsInstallCRD {
		disco.logger.LogInfo("installing and updating Disco CRDs if not already present")
		if err := disco.k8sFramework.CreateDiscoRecordCRDAndWaitUntilReady(); err != nil {
			disco.logger.LogError("cannot create custom resource definitions", err)
		}
	}

	disco.k8sFramework.Run(stopCh)

	disco.logger.LogInfo("waiting for cache to sync...")
	if !disco.k8sFramework.WaitForCacheSync(stopCh) {
		utilruntime.HandleError(errors.New("timed out while waiting for informer caches to sync"))
		return
	}
	disco.logger.LogInfo("cache primed. ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(disco.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(disco.RecheckInterval)
	go func() {
		for {
			select {
			case <-ticker.C:
				disco.requeueAllIngresses()
				disco.requeueAllServices()
				disco.requeueAllDiscoRecords()
				disco.logger.LogInfo(fmt.Sprintf("next check in %v", disco.RecheckInterval.String()))
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
}

func (disco *Operator) runWorker() {
	for disco.processNextWorkItem() {
	}
}

func (disco *Operator) processNextWorkItem() bool {
	obj, quit := disco.queue.Get()
	if quit {
		return false
	}

	err := func(obj interface{}) error {
		defer disco.queue.Done(obj)

		var (
			key string
			ok  bool
		)

		if key, ok = obj.(string); !ok {
			disco.queue.Forget(key)
			utilruntime.HandleError(fmt.Errorf("expected string in workqueue but got %#v", obj))
			return nil
		}

		if err := disco.syncHandler(key); err != nil {
			disco.queue.AddRateLimited(key)
			return fmt.Errorf("error syncing '%s': %s, requeuing", key, err.Error())
		}

		disco.queue.Forget(key)
		disco.logger.LogInfo("successfully synced", "key", key)
		return nil
	}(obj)

	if err != nil {
		utilruntime.HandleError(err)
		return true
	}

	return true
}

// TODO: Refactor this to only handle records.
// Ingress, Service objects would be handled by separate controllers creating the records.
// Remove the recordHelper hack.
func (disco *Operator) syncHandler(key string) error {
	objKind, key, err := splitKeyFuncWithObjKind(key)
	if err != nil {
		return err
	}

	var hosts []string
	rec := newDefaultRecordHelper(disco.Record, disco.ZoneName)

	switch objKind {
	// Handle resources with kind ingress.
	case "ingress":
		o, exists, err := disco.k8sFramework.GetIngressFromIndexerByKey(key)
		if err != nil {
			return errors.Wrapf(err, "%v failed with", key)
		}

		if !exists {
			disco.logger.LogDebug("resource doesn't exist", "key", key)
			return nil
		}

		ingress := o.(*v1beta1.Ingress)
		rec.object = ingress

		if !disco.isTakeCareOfIngress(ingress) {
			disco.logger.LogDebug("ignoring ingress as annotation is not set", "key", key)
			return nil
		}

		recordAnnotation := makeAnnotation(disco.IngressAnnotation, discoAnnotationRecord)
		if val, ok := ingress.GetAnnotations()[recordAnnotation]; ok {
			rec.records = strings.FieldsFunc(val, splitFunc)
		}

		recordTypeAnnotation := makeAnnotation(disco.IngressAnnotation, discoAnnotationRecordType)
		if rt, ok := ingress.GetAnnotations()[recordTypeAnnotation]; ok {
			rec.recordType = stringToRecordsetType(rt)
		}

		recordZoneAnnotation := makeAnnotation(disco.IngressAnnotation, discoAnnotationRecordZoneName)
		if z, ok := ingress.GetAnnotations()[recordZoneAnnotation]; ok {
			rec.zoneName = z
		}

		recordDescriptionAnnotation := makeAnnotation(disco.IngressAnnotation, discoAnnotationRecordDescription)
		if desc, ok := ingress.GetAnnotations()[recordDescriptionAnnotation]; ok {
			rec.description = desc
		}

		for _, r := range ingress.Spec.Rules {
			if r.Host != "" {
				hosts = append(hosts, r.Host)
			}
		}

	// Handle resources with kind service.
	case "service":
		o, exists, err := disco.k8sFramework.GetServiceFromIndexerByKey(key)
		if err != nil {
			return errors.Wrapf(err, "%v failed with", key)
		}

		if !exists {
			disco.logger.LogDebug("resource doesn't exist", "key", key)
			return nil
		}

		service := o.(*v1.Service)

		if !disco.isTakeCareOfService(service) {
			disco.logger.LogDebug("ignoring service as annotation is not set", "key", key)
			return nil
		}

		recordAnnotation := makeAnnotation(disco.ServiceAnnotation, discoAnnotationRecord)
		if val, ok := service.GetAnnotations()[recordAnnotation]; ok {
			hosts = strings.FieldsFunc(val, splitFunc)
		}

		if len(hosts) == 0 {
			disco.logger.LogDebug("ignoring service as annotation record is not set", "key", key)
			return nil
		}

		var ips []string
		for _, ing := range service.Status.LoadBalancer.Ingress {
			if !isSliceContainsStr(ips, ing.IP) {
				ips = append(ips, ing.IP)
			}
		}

		for _, ip := range service.Spec.ExternalIPs {
			if !isSliceContainsStr(ips, ip) {
				ips = append(ips, ip)
			}
		}

		if !isSliceContainsStr(ips, service.Spec.LoadBalancerIP) {
			ips = append(ips, service.Spec.LoadBalancerIP)
		}

		ips = filterEmpty(ips)

		// service record type is always A, because it uses IP addresses from service spec and status
		rec.recordType = RecordsetType.A
		rec.records = ips
		rec.object = service

		recordZoneAnnotation := makeAnnotation(disco.ServiceAnnotation, discoAnnotationRecordZoneName)
		if z, ok := service.GetAnnotations()[recordZoneAnnotation]; ok {
			rec.zoneName = z
		}

		recordDescriptionAnnotation := makeAnnotation(disco.ServiceAnnotation, discoAnnotationRecordDescription)
		if desc, ok := service.GetAnnotations()[recordDescriptionAnnotation]; ok {
			rec.description = desc
		}

	// Handle resource with kind record.
	case strings.ToLower(discoV1.RecordKind):
		o, exists, err := disco.k8sFramework.GetDiscoRecordFromIndexerByKey(key)
		if err != nil {
			return errors.Wrapf(err, "%v failed with", key)
		}

		if !exists {
			disco.logger.LogDebug("resource doesn't exist", "key", key)
			return nil
		}

		discoRecord := o.(*discoV1.Record)
		rec.object = discoRecord

		if val := discoRecord.Spec.Record; val != "" {
			rec.records = strings.FieldsFunc(val, splitFunc)
		}

		if val := discoRecord.Spec.Type; val != "" {
			rec.recordType = stringToRecordsetType(val)
		}

		if val := discoRecord.Spec.ZoneName; val != "" {
			rec.zoneName = val
		}

		if val := discoRecord.Spec.Description; val != "" {
			rec.description = val
		}

		for _, host := range discoRecord.Spec.Hosts {
			hosts = append(hosts, host)
		}

	default:
		disco.logger.LogInfo("unknown resource %q", objKind)
		return nil
	}

	for _, host := range hosts {
		if err := disco.checkRecord(rec, host); err != nil {
			return err
		}
	}

	return nil
}

func (disco *Operator) isTakeCareOfIngress(ingress *v1beta1.Ingress) bool {
	if ingress.GetAnnotations()[disco.IngressAnnotation] == "true" {
		return true
	}
	return false
}

func (disco *Operator) isTakeCareOfService(service *v1.Service) bool {
	if service.GetAnnotations()[disco.ServiceAnnotation] == "true" {
		return true
	}
	return false
}

func (disco *Operator) checkRecord(discoRecord *recordHelper, host string) error {
	labels := prometheus.Labels{
		"kind": discoRecord.getKind(),
		"key":  discoRecord.getKey(),
		"host": host,
	}

	// Allow recordset in different DNS zone.
	zoneName := disco.ZoneName
	if zoneNameOverride := discoRecord.zoneName; zoneNameOverride != "" {
		zoneName = zoneNameOverride
	}

	disco.logger.LogDebug("ensuring record", "host", host, "type", discoRecord.recordType, "record", strings.Join(discoRecord.records, ","), "zone", zoneName)
	zone, err := disco.getZoneByName(zoneName)
	if err != nil {
		return err
	}

	recordsetList, err := disco.dnsV2Client.listDesignateRecordsetsForZone(zone, host)
	if err != nil {
		return err
	}

	var recordsetID string
	for _, rs := range recordsetList {
		if ensureFQDN(host) == ensureFQDN(rs.Name) {
			recordsetID = rs.ID
		}
	}

	// Cleanup if there was an attempt to delete the ingress, service or record.
	isHasDeletionTimestamp, err := k8sutils.HasDeletionTimestamp(discoRecord.object)
	if err != nil {
		return err
	}
	// Delete the recordset if if still exists in designate.
	if isHasDeletionTimestamp && recordsetID != "" {
		if err := disco.dnsV2Client.deleteDesignateRecordset(host, recordsetID, zone.ID); err != nil {
			metrics.RecordsetDeletionFailedCounter.With(labels).Inc()
			return err
		 }
		metrics.RecordsetDeletionSuccessCounter.With(labels).Inc()
	}
	// Remove the finalizer and allow the ingress, service or record to be deleted.
	if isHasDeletionTimestamp {
		return disco.k8sFramework.EnsureDiscoFinalizerRemoved(discoRecord.object)
	}

	if recordsetID != "" {
		disco.logger.LogDebug("recordset already exists", "host", host, "zone", zone.Name)
		return nil
	}

	// Ensure the finalizer exists before creating a record.
	if err := disco.k8sFramework.EnsureDiscoFinalizerExists(discoRecord.object); err != nil {
		return err
	}

	records := strings.FieldsFunc(disco.Record, splitFunc)
	if rec := discoRecord.records; len(rec) > 0 {
		records = rec
	}

	recordType := RecordsetType.CNAME
	if rt := discoRecord.recordType; rt != "" {
		recordType = stringToRecordsetType(rt)
	}

	// Only make it a FQDN if not an IP address.
	if recordType != RecordsetType.A {
		for i, v := range records {
			records[i] = ensureFQDN(v)
		}
	}

	description := discoRecordsetDescription
	if desc := discoRecord.description; desc != "" {
		description = desc
	}

	if err := disco.dnsV2Client.createDesignateRecordset(
		zone.ID,
		ensureFQDN(host),
		records,
		disco.RecordsetTTL,
		recordType,
		description,
	); err != nil {
		metrics.RecordsetCreationFailedCounter.With(labels).Inc()
		return err
	}

	metrics.RecordsetCreationSuccessCounter.With(labels).Inc()
	disco.logger.LogInfo("create recordset successful", "key", discoRecord.getKey(), "host", host, "record", strings.Join(records, ","), "zone", ensureFQDN(zone.Name), "recordType", recordType)
	disco.k8sFramework.Eventf(discoRecord.object, v1.EventTypeNormal, createEvent, "create recordset on %s %s successful", discoRecord.getKind(), discoRecord.getKey())

	return nil
}

func (disco *Operator) getZoneByName(zoneName string) (zones.Zone, error) {
	if o, ok := disco.zoneCache.Get(zoneName); ok {
		zone := o.(zones.Zone)
		disco.logger.LogDebug("found zone in cache", "zone", zone.Name)
		return zone, nil
	}

	zone, err := disco.dnsV2Client.getDesignateZoneByName(zoneName)
	if err != nil {
		return zone, err
	}

	disco.zoneCache.Set(zoneName, zone, expiringCache.DefaultExpiration)
	return zone, nil
}

func (disco *Operator) requeueAllIngresses() {
	for _, o := range disco.k8sFramework.GetIngressInformerStore().List() {
		disco.enqueueItem(o)
	}
}

func (disco *Operator) requeueAllServices() {
	for _, o := range disco.k8sFramework.GetServiceInformerStore().List() {
		disco.enqueueItem(o)
	}
}

func (disco *Operator) requeueAllDiscoRecords() {
	for _, o := range disco.k8sFramework.GetDiscoRecordInformerStore().List() {
		disco.enqueueItem(o)
	}
}

func (disco *Operator) enqueueItem(obj interface{}) {
	key, err := keyFunc(obj)
	if err != nil {
		utilruntime.HandleError(err)
		return
	}
	disco.queue.AddRateLimited(key)
	disco.logger.LogDebug("adding item to queue", "key", key)
}
