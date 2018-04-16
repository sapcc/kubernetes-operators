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

package fusion

import (
	"fmt"
	"reflect"
	"sync"
	"time"

	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/client-go/informers/core/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
)

var (
	// VERSION of the fusion
	VERSION = "0.0.0.dev"
)

// Operator is the CNAME operator (fusion)
type Operator struct {
	Options

	clientset  *kubernetes.Clientset
	cmInformer cache.SharedIndexInformer

	ResyncPeriod  time.Duration
	RecheckPeriod time.Duration

	prometheusConfigmapData map[string]string
}

// New creates a new operator using the given options
func New(options Options) *Operator {

	LogInfo("Creating new Prometheus Fusion in version %v\n", VERSION)

	if err := options.CheckOptions(); err != nil {
		LogInfo(err.Error())
	}

	resyncPeriod := time.Duration(options.ResyncPeriod) * time.Minute
	recheckPeriod := time.Duration(options.RecheckPeriod) * time.Minute

	kubeConfig := newClientConfig(options)
	if kubeConfig == nil {
		LogFatal("Unable to create kubeConfig. Aborting")
	}

	clientset, err := kubernetes.NewForConfig(kubeConfig)
	if err != nil {
		LogFatal("Couldn't create Kubernetes client: %s", err)
	}

	operator := &Operator{
		Options:                 options,
		clientset:               clientset,
		ResyncPeriod:            resyncPeriod,
		RecheckPeriod:           recheckPeriod,
		prometheusConfigmapData: map[string]string{},
	}

	cmInformer := v1.NewConfigMapInformer(
		clientset,
		"",
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	cmInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.configMapAdd,
		UpdateFunc: operator.configMapUpdate,
		DeleteFunc: operator.configMapDelete,
	})
	operator.cmInformer = cmInformer

	return operator
}

// Run starts the operator
func (fusion *Operator) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer runtime.HandleCrash()
	defer wg.Done()
	wg.Add(1)

	LogInfo("Ladies and Gentlemen, Prometheus Fusion! Fusing your prometheus rules and alerts now in version %v\n", VERSION)

	go fusion.cmInformer.Run(stopCh)

	LogInfo("Waiting for cache to sync...")
	cache.WaitForCacheSync(
		stopCh,
		fusion.cmInformer.HasSynced,
	)
	LogInfo("Cache primed. Ready for operations.")

	LogInfo("Considering only configmaps with annotation: %v", fusion.ConfigmapAnnotation)

	ticker := time.NewTicker(fusion.RecheckPeriod)
	go func() {
		for {
			select {
			case <-ticker.C:
				fusion.collectAndMergeRules()
				LogInfo("Next check in %v", fusion.RecheckPeriod)
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
}

func (fusion *Operator) configMapAdd(obj interface{}) {
	cm := obj.(*corev1.ConfigMap)
	if fusion.isTakeCareOfConfigMap(cm) {
		LogInfo("found configmap %s/%s", cm.GetNamespace(), cm.GetName())
		fusion.collectAndMergeRules()
	}
}

func (fusion *Operator) configMapUpdate(old, new interface{}) {
	cmOld := old.(*corev1.ConfigMap)
	cmNew := new.(*corev1.ConfigMap)

	if fusion.isTakeCareOfConfigMap(cmOld) || fusion.isTakeCareOfConfigMap(cmNew) {
		if fusion.isConfigMapNeedsUpdate(cmNew, cmOld) {
			LogDebug("Updated configmap %s/%s", cmOld.GetNamespace(), cmOld.GetName())
			fusion.collectAndMergeRules()
			return
		}
		LogDebug("Nothing changed in configmap %s/%s", cmOld.GetNamespace(), cmOld.GetName())
	}
}

func (fusion *Operator) configMapDelete(obj interface{}) {
	cm := obj.(*corev1.ConfigMap)
	if fusion.isTakeCareOfConfigMap(cm) {
		LogInfo("deleted configmap %s/%s", cm.GetNamespace(), cm.GetName())
		fusion.collectAndMergeRules()
	}
}

func (fusion *Operator) getUpstreamConfigMap(namespace, name string) (*corev1.ConfigMap, error) {
	LogDebug("get upstream configmap %s/%s", namespace, name)
	return fusion.clientset.CoreV1().ConfigMaps(namespace).Get(name, metav1.GetOptions{})
}

func (fusion *Operator) updateUpstreamConfigMap(cm *corev1.ConfigMap) error {
	LogDebug("updating upstream configmap %s/%s", cm.GetNamespace(), cm.GetName())
	_, err := fusion.clientset.CoreV1().ConfigMaps(cm.GetNamespace()).Update(cm)
	return err
}

func (fusion *Operator) isConfigMapNeedsUpdate(cmNew, cmOld *corev1.ConfigMap) bool {
	if !reflect.DeepEqual(cmOld.Data, cmNew.Data) || !reflect.DeepEqual(cmOld.GetAnnotations(), cmNew.GetAnnotations()) {
		return true
	}
	return false
}

func (fusion *Operator) isTakeCareOfConfigMap(cm *corev1.ConfigMap) bool {
	if cm.GetAnnotations()[fusion.ConfigmapAnnotation] == "true" {
		return true
	}
	return false
}

// discoverPrometheusConfigMap discovers Prometheus' configmap via annotation if namespace,name is not provided. returns an error if nothing can be found
func (fusion *Operator) gotOrDiscoverPrometheusConfigmap() error {
	if fusion.PrometheusConfigMapNamespace == "" || fusion.PrometheusConfigMapName == "" {
		LogInfo("Namespace/Name of Prometheus configmap not provided. Trying discovery")
		for _, o := range fusion.cmInformer.GetIndexer().List() {
			cm := o.(*corev1.ConfigMap)
			if cm.GetAnnotations()[PrometheusConfigMapAnnotation] == "true" {
				fusion.PrometheusConfigMapNamespace = cm.GetNamespace()
				fusion.PrometheusConfigMapName = cm.GetName()
				LogInfo("Discovered prometheus configmap %v/%v", cm.GetNamespace(), cm.GetName())
				return nil
			}
		}
		return errors.New("Could not discover prometheus configmap")
	}
	return nil
}

func (fusion *Operator) collectAndMergeRules() {
	if err := fusion.gotOrDiscoverPrometheusConfigmap(); err != nil {
		runtime.HandleError(err)
	}

	if err := fusion.collectRules(); err != nil {
		runtime.HandleError(err)
	}

	if err := fusion.generatePrometheusConfigmap(); err != nil {
		runtime.HandleError(err)
	}
}

func (fusion *Operator) collectRules() error {
	for _, o := range fusion.cmInformer.GetStore().List() {
		cm := o.(*corev1.ConfigMap)
		if fusion.isTakeCareOfConfigMap(cm) {
			if errs := fuseMaps(fusion.prometheusConfigmapData, cm.Data); errs != nil {
				return fmt.Errorf("Failed to merge rules of configmap %s/%s: %v ", cm.GetNamespace(), cm.GetName(), errs)
			}
			LogInfo("Collected rules from configmap %s/%s", cm.GetNamespace(), cm.GetName())
		}
	}
	return nil
}

func (fusion *Operator) generatePrometheusConfigmap() error {
	defer func() {
		// clear prometheus cm before next run
		fusion.prometheusConfigmapData = map[string]string{}
	}()

	curCM, err := fusion.getUpstreamConfigMap(fusion.PrometheusConfigMapNamespace, fusion.PrometheusConfigMapName)
	if err != nil {
		return err
	}

	newCM := curCM.DeepCopy()
	newCM.Data = fusion.prometheusConfigmapData

	// preserve prometheus configuration if in same file
	for _, key := range fusion.PreservedConfigmapKeys {
		if data, ok := curCM.Data[key]; ok {
			newCM.Data[key] = data
		}
	}

	if fusion.isConfigMapNeedsUpdate(curCM, newCM) {
		LogInfo("generating prometheus configmap and updating upstream")
		return fusion.updateUpstreamConfigMap(newCM)
	}

	LogInfo("checked rules and alerts. no update.")
	return nil
}
