/*******************************************************************************
*
* Copyright 2018 SAP SE
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
	"sync"
	"time"

	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus"
	"k8s.io/api/extensions/v1beta1"
	"k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	v1beta12 "k8s.io/client-go/informers/extensions/v1beta1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

var (
	// VERSION of the disco
	VERSION = "0.0.0.dev"
)

// Operator is the CNAME operator (disco)
type Operator struct {
	Options
	*Config

	dnsV2Client     *DNSV2Client
	clientset       *kubernetes.Clientset
	ingressInformer cache.SharedIndexInformer

	// ResyncPeriod defines the period after which the local cache of ingresses is refreshed
	ResyncPeriod    time.Duration
	RecheckInterval time.Duration

	queue workqueue.RateLimitingInterface
}

// New creates a new operator using the given options
func New(options Options) *Operator {
	LogDebug("starting DISCO in version %v\n", VERSION)

	if err := options.CheckOptions(); err != nil {
		LogFatal(err.Error())
		return nil
	}

	discoConfig, err := ReadConfig(options.ConfigPath)
	if err != nil {
		LogFatal("failed to read config: %v", err)
		return nil
	}

	resyncPeriod := time.Duration(options.ResyncPeriod) * time.Minute
	recheckInterval := time.Duration(options.RecheckPeriod) * time.Minute

	kubeConfig, err := newClientConfig(options)
	if err != nil {
		LogFatal("couldn't create Kubernetes client config: %v", err)
		return nil
	}

	clientset, err := kubernetes.NewForConfig(kubeConfig)
	if err != nil {
		LogFatal("couldn't create Kubernetes client: %v", err)
		return nil
	}

	dnsV2Client, err := NewDNSV2ClientFromAuthOpts(discoConfig.AuthOpts)
	if err != nil {
		LogFatal("unable to create designate v2 client: %v", err)
		return nil
	}

	operator := &Operator{
		Options:         options,
		clientset:       clientset,
		dnsV2Client:     dnsV2Client,
		Config:          discoConfig,
		ResyncPeriod:    resyncPeriod,
		RecheckInterval: recheckInterval,
		queue:           workqueue.NewRateLimitingQueue(workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second)),
	}

	ingressInformer := v1beta12.NewIngressInformer(
		clientset,
		"",
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.ingressAdd,
		UpdateFunc: operator.ingressUpdate,
		DeleteFunc: operator.ingressDelete,
	})

	operator.ingressInformer = ingressInformer

	return operator
}

// Run starts the operator
func (disco *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer runtime.HandleCrash()
	defer disco.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)

	LogInfo("Ladies and Gentlemen, the DISCO is about to begin! Creating your OpenStack Designate CNAMEs now in version %v\n", VERSION)

	go disco.ingressInformer.Run(stopCh)

	LogInfo("waiting for cache to sync...")
	cache.WaitForCacheSync(
		stopCh,
		disco.ingressInformer.HasSynced,
	)
	LogInfo("cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(disco.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(disco.RecheckInterval)
	go func() {
		for {
			select {
			case <-ticker.C:
				disco.requeueAllIngresses()
				LogInfo("next check in %v", disco.RecheckInterval)
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
	key, quit := disco.queue.Get()
	if quit {
		return false
	}
	defer disco.queue.Done(key)

	// do your work on the key.  This method will contains your "do stuff" logic
	err := disco.syncHandler(key.(string))
	if err == nil {
		disco.queue.Forget(key)
		return true
	}

	LogError("%v failed with : %v", key, err)
	disco.queue.AddRateLimited(key)

	return true
}

func (disco *Operator) handleError(err error, key interface{}) {
	if err == nil {
		disco.queue.Forget(key)
		return
	}

	if disco.queue.NumRequeues(key) < 5 {
		LogError("error syncing pod %v: %v", key, err)

		// Re-enqueue the key rate limited. Based on the rate limiter on the
		// queue and the re-enqueue history, the key will be processed later again.
		disco.queue.AddRateLimited(key)
		return
	}

	disco.queue.Forget(key)

	// Report to an external entity that, even after several retries, we could not successfully process this key
	runtime.HandleError(err)
	LogInfo("dropping pod %q out of the queue: %v", key, err)

}

func (disco *Operator) syncHandler(key string) error {
	o, exists, err := disco.ingressInformer.GetStore().GetByKey(key)
	if err != nil {
		return errors.Wrapf(err, "%v failed with : %v", key)
	}

	if !exists {
		LogInfo("deleted ingress %v", key)
		return nil
	}

	ingress := o.(*v1beta1.Ingress)

	if disco.isTakeCareOfIngress(ingress) {
		for _, rule := range ingress.Spec.Rules {
			if rule.Host != "" {
				LogInfo("checking ingress %v/%v, hosts: %v", ingress.GetNamespace(), ingress.GetName(), rule.Host)
				if err := disco.checkRecords(ingress, rule.Host); err != nil {
					return err
				}
			}
		}
	} else {
		LogDebug("ignoring ingress %v/%v as annotation was not set", ingress.GetNamespace(), ingress.GetName())
	}
	return err
}

func (disco *Operator) requeueAllIngresses() {
	for _, o := range disco.ingressInformer.GetStore().List() {
		i := o.(*v1beta1.Ingress)
		key, err := cache.MetaNamespaceKeyFunc(o)
		if err != nil {
			LogError("couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
		}
		LogDebug("added ingress %s/%s", i.GetNamespace(), i.GetName())
		disco.queue.AddRateLimited(key)
	}
}

func (disco *Operator) isTakeCareOfIngress(ingress *v1beta1.Ingress) bool {
	if ingress.GetAnnotations()[disco.IngressAnnotation] == "true" {
		return true
	}
	return false
}

func (disco *Operator) checkRecords(ingress *v1beta1.Ingress, host string) error {
	labels := prometheus.Labels{
		"ingress": fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName()),
		"host":    host,
	}
	initializeFailureMetrics(labels)

	//TODO: maybe use https://github.com/patrickmn/go-cache instead of listing recordsets every time
	zone, err := disco.dnsV2Client.getDesignateZoneByName(disco.ZoneName)
	if err != nil {
		return err
	}

	recordsetList, err := disco.dnsV2Client.listDesignateRecordsetsForZone(zone, host)
	if err != nil {
		return err
	}

	var recordsetID string
	for _, rs := range recordsetList {
		if addSuffixIfRequired(host) == addSuffixIfRequired(rs.Name) {
			recordsetID = rs.ID
		}
	}

	// add finalizer before creating anything. return an
	if err := disco.ensureDiscoFinalizerExists(ingress); err != nil {
		return errors.Wrapf(err, "will not create recordset in this cycle. failed to add finalizer %v", DiscoFinalizer)
	}

	// there was an attempt to delete the ingress. cleanup recordset
	if ingressHasDeletionTimestamp(ingress) {
		if recordsetID == "" {
			return fmt.Errorf("would delete recordset %s in zone %s but was unable to find its uid", host, zone.Name)
		}
		if err := disco.dnsV2Client.deleteDesignateRecordset(host, recordsetID, zone.ID); err != nil {
			recordsetDeletionFailedCounter.With(labels).Inc()
			return err
		}
		recordsetDeletionSuccessCounter.With(labels).Inc()
		return disco.ensureDiscoFinalizerRemoved(ingress)
	}

	if recordsetID != "" {
		LogDebug("recordset for host %v in zone %v already exists", host, zone.Name)
		return nil
	}

	record := disco.Record
	if rec, ok := ingress.GetAnnotations()[DiscoAnnotationRecord]; ok {
		record = addSuffixIfRequired(rec)
	}

	recordType := RecordsetType.CNAME
	if rt, ok := ingress.GetAnnotations()[DiscoAnnotationRecordType]; ok {
		recordType = stringToRecordsetType(rt)
	}

	description := ""
	if desc, ok := ingress.GetAnnotations()[DiscoAnnotationRecordDescription]; ok {
		description = desc
	}

	if err := disco.dnsV2Client.createDesignateRecordset(
		zone.ID,
		addSuffixIfRequired(host),
		[]string{record},
		disco.RecordsetTTL,
		recordType,
		description,
	); err != nil {
		recordsetCreationFailedCounter.With(labels).Inc()
		return err
	}
	recordsetCreationSuccessCounter.With(labels).Inc()
	return nil
}

func (disco *Operator) ingressAdd(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		LogError("couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
		return
	}
	disco.queue.AddRateLimited(key)
}

func (disco *Operator) ingressUpdate(old, new interface{}) {
	iOld := old.(*v1beta1.Ingress)
	iNew := new.(*v1beta1.Ingress)

	if disco.isIngressNeedsUpdate(iNew, iOld) {
		LogDebug("updated ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		key, err := cache.MetaNamespaceKeyFunc(new)
		if err != nil {
			LogError("couldn't add ingress %s/%s", iNew.GetNamespace(), iNew.GetName())
		}
		disco.queue.AddRateLimited(key)
		return
	}
	LogDebug("nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
}

func (disco *Operator) updateUpstreamIngress(ingress *v1beta1.Ingress) error {
	_, err := disco.clientset.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).Update(ingress)
	return err
}

func (disco *Operator) isIngressNeedsUpdate(iNew, iOld *v1beta1.Ingress) bool {
	if !reflect.DeepEqual(iOld.Spec, iNew.Spec) || !reflect.DeepEqual(iOld.GetAnnotations(), iNew.GetAnnotations()) {
		return true
	}
	return false
}

func (disco *Operator) ingressDelete(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		LogError("couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
		return
	}
	disco.queue.AddRateLimited(key)
	LogInfo("ingress %s/%s was deleted", i.GetNamespace(), i.GetName())
}

func (disco *Operator) ensureDiscoFinalizerExists(ingress *v1beta1.Ingress) error {
	// add finalizer if not present and ingress was not deleted
	if !ingressHasDiscoFinalizer(ingress) && !ingressHasDeletionTimestamp(ingress) {
		copy := ingress.DeepCopy()
		copy.Finalizers = append(copy.GetFinalizers(), DiscoFinalizer)
		return disco.updateUpstreamIngress(copy)
	}
	return nil
}

func (disco *Operator) ensureDiscoFinalizerRemoved(ingress *v1beta1.Ingress) error {
	// do not remove finalizer if DeletionTimestamp is not set
	if ingressHasDiscoFinalizer(ingress) && ingressHasDeletionTimestamp(ingress) {
		copy := ingress.DeepCopy()
		for i, fin := range copy.GetFinalizers() {
			if fin == DiscoFinalizer {
				// delete but preserve order
				copy.Finalizers = append(copy.Finalizers[:i], copy.Finalizers[i+1:]...)
				return disco.updateUpstreamIngress(copy)
			}
		}
	}
	return nil
}
