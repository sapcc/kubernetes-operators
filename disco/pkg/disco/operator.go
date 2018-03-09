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

	"github.com/gophercloud/gophercloud"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
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
	Config

	dnsV2Client     *gophercloud.ServiceClient
	clientset       *kubernetes.Clientset
	ingressInformer cache.SharedIndexInformer

	// ResyncPeriod defines the period after which the local cache of ingresses is refreshed
	ResyncPeriod    time.Duration
	RecheckInterval time.Duration

	recordsetList []recordsets.RecordSet

	queue workqueue.RateLimitingInterface
}

// New creates a new operator using the given options
func New(options Options) *Operator {
	LogInfo("Starting DISCO in version %v\n", VERSION)

	if err := options.CheckOptions(); err != nil {
		LogFatal(err.Error())
	}

	discoConfig, err := ReadConfig(options.ConfigPath)
	if err != nil {
		LogFatal("Could get configuration: %v. Aborting.", err)
	}

	resyncPeriod := time.Duration(options.ResyncPeriod) * time.Minute
	recheckInterval := time.Duration(options.RecheckPeriod) * time.Minute

	kubeConfig, err := newClientConfig(options)
	if err != nil {
		LogFatal("Couldn't create Kubernetes client config: %v", err)
	}

	clientset, err := kubernetes.NewForConfig(kubeConfig)
	if err != nil {
		LogFatal("Couldn't create Kubernetes client: %v", err)
	}

	token, err := getToken(discoConfig.AuthOpts)
	if err != nil {
		LogFatal("Could not obtain token: %v", err)
	}
	discoConfig.AuthOpts.token = token

	dnsV2Client, err := newOpenStackDesignateClient(discoConfig.AuthOpts)
	if err != nil {
		LogFatal("Unable to create designate v2 client: %v", err)
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

	LogInfo("Waiting for cache to sync...")
	cache.WaitForCacheSync(
		stopCh,
		disco.ingressInformer.HasSynced,
	)
	LogInfo("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(disco.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(disco.RecheckInterval)
	go func() {
		for {
			select {
			case <-ticker.C:
				disco.requeueAllIngresses()
				LogInfo("Next check in %v", disco.RecheckInterval)
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
		LogInfo("Error syncing pod %v: %v", key, err)

		// Re-enqueue the key rate limited. Based on the rate limiter on the
		// queue and the re-enqueue history, the key will be processed later again.
		disco.queue.AddRateLimited(key)
		return
	}

	disco.queue.Forget(key)
	// Report to an external entity that, even after several retries, we could not successfully process this key
	runtime.HandleError(err)
	LogInfo("Dropping pod %q out of the queue: %v", key, err)

}

func (disco *Operator) syncHandler(key string) error {
	o, exists, err := disco.ingressInformer.GetStore().GetByKey(key)
	if err != nil {
		return errors.Wrapf(err, "%v failed with : %v", key)
	}

	if !exists {
		LogInfo("Deleted ingress %v", key)
		return nil
	}

	ingress := o.(*v1beta1.Ingress)

	if disco.isTakeCareOfIngress(ingress) {
		for _, rule := range ingress.Spec.Rules {
			if rule.Host != "" {
				LogDebug("Checking ingress %v/%v: Hosts: %v", ingress.GetNamespace(), ingress.GetName(), rule.Host)
				//TODO: SANs?
				return disco.checkRecords(ingress, rule.Host)
			}
		}
	} else {
		LogDebug("Ignoring ingress %v/%v as annotation was not set", ingress.GetNamespace(), ingress.GetName())
	}
	return err
}

func (disco *Operator) requeueAllIngresses() {
	for _, o := range disco.ingressInformer.GetStore().List() {
		i := o.(*v1beta1.Ingress)
		key, err := cache.MetaNamespaceKeyFunc(o)
		if err != nil {
			LogError("Couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
		}
		LogDebug("Added ingress %s/%s", i.GetNamespace(), i.GetName())
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
	zone, err := getDesignateZoneByName(disco.dnsV2Client, disco.ZoneName)
	if err != nil {
		return err
	}

	recordsetList, err := listDesignateRecordsetsForZone(disco.dnsV2Client, zone)
	if err != nil {
		return err
	}

	for _, rs := range recordsetList {
		if host == rs.Name {
			return nil
		}
	}

	if err := createDesignateRecordset(
		disco.dnsV2Client,
		zone.ID,
		addSuffixIfRequired(host),
		[]string{disco.Record},
		disco.RecordsetTTL,
		RecordsetType.CNAME,
	); err != nil {
		return err
	}

	return nil
}

func (disco *Operator) ingressAdd(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		LogError("Couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
	}
	disco.queue.AddRateLimited(key)
}

func (disco *Operator) ingressUpdate(old, new interface{}) {
	iOld := old.(*v1beta1.Ingress)
	iNew := new.(*v1beta1.Ingress)

	if disco.isIngressNeedsUpdate(iNew, iOld) {
		LogDebug("Updated ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		key, err := cache.MetaNamespaceKeyFunc(new)
		if err != nil {
			LogError("Couldn't add ingress %s/%s", iNew.GetNamespace(), iNew.GetName())
		}
		disco.queue.AddRateLimited(key)
		return
	}
	LogDebug("Nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
}

func (disco *Operator) isIngressNeedsUpdate(iNew, iOld *v1beta1.Ingress) bool {
	if !reflect.DeepEqual(iOld.Spec, iNew.Spec) || !reflect.DeepEqual(iOld.GetAnnotations(), iNew.GetAnnotations()) {
		return true
	}
	return false
}

func (disco *Operator) ingressDelete(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	if len(i.Spec.Rules) > 0 {
		rules := []string{}
		for _, rule := range i.Spec.Rules {
			rules = append(rules, rule.Host)
		}
		LogInfo("Ingress %s/%s was deleted and contains rules for hosts: %v", i.GetNamespace(), i.GetName(), rules)

		//TODO: How about deleting CNAMEs?

		return
	}
	LogInfo("Ingress %s/%s was deleted and didn't contain rules for hosts", i.GetNamespace(), i.GetName())
}
