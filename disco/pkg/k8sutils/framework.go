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

package k8sutils

import (
	"context"
	"fmt"
	"time"

	"github.com/pkg/errors"
	discov1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco/v1"
	"github.com/sapcc/kubernetes-operators/disco/pkg/config"
	genCRDClientset "github.com/sapcc/kubernetes-operators/disco/pkg/generated/clientset/versioned"
	discoClientV1 "github.com/sapcc/kubernetes-operators/disco/pkg/generated/clientset/versioned/typed/disco/v1"
	genCRDInformers "github.com/sapcc/kubernetes-operators/disco/pkg/generated/informers/externalversions"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
	coreV1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	extensionsobj "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1beta1"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
	apimetav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachineryWatch "k8s.io/apimachinery/pkg/watch"
	corev1informers "k8s.io/client-go/informers/core/v1"
	v1beta1informers "k8s.io/client-go/informers/extensions/v1beta1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	v12 "k8s.io/client-go/kubernetes/typed/core/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/tools/watch"
)

// WaitTimeout is the time we're waiting before considering an operation failed.
const WaitTimeout = 2 * time.Minute

// K8sFramework ..
type K8sFramework struct {
	*kubernetes.Clientset
	CRDclientset      *apiextensionsclient.Clientset
	DiscoCRDClientset *discoClientV1.DiscoV1Client

	logger                  log.Logger
	kubeConfig              *rest.Config
	eventRecorder           record.EventRecorder
	finalizer               string
	discoCRDInformerFactory genCRDInformers.SharedInformerFactory
	ingressInformer         cache.SharedIndexInformer
	serviceInformer         cache.SharedIndexInformer
	discoCRDInformer        cache.SharedIndexInformer
}

// NewK8sFramework creates a new K8sFramework.
func NewK8sFramework(options config.Options, logger log.Logger) (*K8sFramework, error) {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}
	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}

	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		return nil, err
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	crdclientset, err := apiextensionsclient.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	discoCRDClient, err := discoClientV1.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	crdClient, err := genCRDClientset.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	if err := discov1.AddToScheme(scheme.Scheme); err != nil {
		return nil, err
	}

	b := record.NewBroadcaster()
	b.StartLogging(logger.LogEvent)
	b.StartRecordingToSink(&v12.EventSinkImpl{
		Interface: clientset.CoreV1().Events(apimetav1.NamespaceAll),
	})
	eventRecorder := b.NewRecorder(scheme.Scheme, coreV1.EventSource{
		Component: options.EventComponent,
	})

	ingressInformer := v1beta1informers.NewIngressInformer(
		clientset,
		apimetav1.NamespaceAll,
		options.ResyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	serviceInformer := corev1informers.NewServiceInformer(
		clientset,
		apimetav1.NamespaceAll,
		options.ResyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	informerFactory := genCRDInformers.NewSharedInformerFactory(crdClient, options.ResyncPeriod)
	discoCRDInformer := informerFactory.Disco().V1().Records().Informer()

	return &K8sFramework{
		Clientset:               clientset,
		finalizer:               options.Finalizer,
		kubeConfig:              config,
		eventRecorder:           eventRecorder,
		ingressInformer:         ingressInformer,
		serviceInformer:         serviceInformer,
		discoCRDInformer:        discoCRDInformer,
		CRDclientset:            crdclientset,
		DiscoCRDClientset:       discoCRDClient,
		discoCRDInformerFactory: informerFactory,
		logger:                  log.NewLoggerWith(logger, "component", "k8sFramework"),
	}, nil
}

// Run starts the informers.
func (k8s *K8sFramework) Run(stopCh <-chan struct{}) {
	go k8s.discoCRDInformerFactory.Start(stopCh)
	go k8s.discoCRDInformer.Run(stopCh)
	go k8s.ingressInformer.Run(stopCh)
	go k8s.serviceInformer.Run(stopCh)
}

// WaitForCacheSync returns true if all caches have been synced.
func (k8s *K8sFramework) WaitForCacheSync(stopCh <-chan struct{}) bool {
	return cache.WaitForCacheSync(
		stopCh,
		k8s.discoCRDInformer.HasSynced,
		k8s.ingressInformer.HasSynced,
		k8s.serviceInformer.HasSynced,
	)
}

// AddIngressInformerEventHandler adds event handlers to the ingress informer.
func (k8s *K8sFramework) AddIngressInformerEventHandler(addFunc, deleteFunc func(obj interface{}), updateFunc func(oldObj, newObj interface{})) {
	k8s.ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    addFunc,
		UpdateFunc: updateFunc,
		DeleteFunc: deleteFunc,
	})
}

// GetIngressFromIndexerByKey gets an ingress from the ingress informer indexer by key.
func (k8s *K8sFramework) GetIngressFromIndexerByKey(key string) (interface{}, bool, error) {
	return k8s.ingressInformer.GetIndexer().GetByKey(key)
}

// GetIngressInformerStore returns the ingress infromer store.
func (k8s *K8sFramework) GetIngressInformerStore() cache.Store {
	return k8s.ingressInformer.GetStore()
}

// AddServiceInformerEventHandler adds event handlers to the service informer.
func (k8s *K8sFramework) AddServiceInformerEventHandler(addFunc, deleteFunc func(obj interface{}), updateFunc func(oldObj, newObj interface{})) {
	k8s.serviceInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    addFunc,
		UpdateFunc: updateFunc,
		DeleteFunc: deleteFunc,
	})
}

// GetServiceFromIndexerByKey returns the Service from the informer indexer by key.
func (k8s *K8sFramework) GetServiceFromIndexerByKey(key string) (interface{}, bool, error) {
	return k8s.serviceInformer.GetIndexer().GetByKey(key)
}

// GetServiceInformerStore returns the service infromer store.
func (k8s *K8sFramework) GetServiceInformerStore() cache.Store {
	return k8s.serviceInformer.GetStore()
}

// GetDiscoRecordFromIndexerByKey returns the Record from the informer indexer by key.
func (k8s *K8sFramework) GetDiscoRecordFromIndexerByKey(key string) (interface{}, bool, error) {
	return k8s.discoCRDInformer.GetIndexer().GetByKey(key)
}

// GetDiscoRecordInformerStore returns the discoRecord informer store.
func (k8s *K8sFramework) GetDiscoRecordInformerStore() cache.Store {
	return k8s.discoCRDInformer.GetStore()
}

// AddDiscoCRDInformerEventHandler adds event handlers to the disco informer.
func (k8s *K8sFramework) AddDiscoCRDInformerEventHandler(addFunc, deleteFunc func(obj interface{}), updateFunc func(oldObj, newObj interface{})) {
	k8s.discoCRDInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    addFunc,
		UpdateFunc: updateFunc,
		DeleteFunc: deleteFunc,
	})
}

// Eventf emits an event via the event recorder.
func (k8s *K8sFramework) Eventf(object runtime.Object, eventType, reason, messageFmt string, args ...interface{}) {
	k8s.eventRecorder.Eventf(object, eventType, reason, messageFmt, args...)
}

// CreateDiscoRecordCRDAndWaitUntilReady creates the CRDs used by this operator and waits until they are ready or the operation times out.
func (k8s *K8sFramework) CreateDiscoRecordCRDAndWaitUntilReady() error {
	ctx := context.TODO()
	crd := NewDiscoRecordCRD()
	crdClient := k8s.CRDclientset.ApiextensionsV1beta1().CustomResourceDefinitions()
	oldCRD, err := crdClient.Get(ctx, crd.Name, metaV1.GetOptions{})
	if err != nil && !apiErrors.IsNotFound(err) {
		return errors.Wrapf(err, "error getting crd")
	}
	if apiErrors.IsNotFound(err) {
		k8s.logger.LogInfo("creating CRD", "group", crd.GetObjectKind().GroupVersionKind().Group, "name", crd.GetName())
		if _, err := crdClient.Create(ctx, crd, metaV1.CreateOptions{}); err != nil {
			return errors.Wrap(err, "error creating crd")
		}
	}
	if err == nil {
		k8s.logger.LogInfo("updating CRD", "group", crd.GetObjectKind().GroupVersionKind().Group, "name", crd.GetName())
		crd.ResourceVersion = oldCRD.GetResourceVersion()
		if _, err := crdClient.Update(ctx, crd, metaV1.UpdateOptions{}); err != nil {
			return errors.Wrap(err, "error updating crd")
		}
	}

	return k8s.waitForUpstreamCRD(crd)
}

// GetIngress returns the ingress or an error.
func (k8s *K8sFramework) GetIngress(namespace, name string) (*extensionsv1beta1.Ingress, error) {
	ctx := context.TODO()
	return k8s.ExtensionsV1beta1().Ingresses(namespace).Get(ctx, name, metaV1.GetOptions{})
}

// UpdateIngressAndWait updates an existing Ingress and waits until the operation times out or is completed.
func (k8s *K8sFramework) UpdateIngressAndWait(oldIngress, newIngress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
	ctx := context.TODO()
	oldIngress, err := k8s.GetIngress(oldIngress.GetNamespace(), oldIngress.GetName())
	if err != nil {
		return err
	}

	// Nothing to update.
	if !isIngressNeedsUpdate(oldIngress, newIngress) {
		return nil
	}

	updatedIngress, err := k8s.ExtensionsV1beta1().Ingresses(oldIngress.GetNamespace()).Update(ctx, newIngress, metaV1.UpdateOptions{})
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("updating ingress", "key", fmt.Sprintf("%s/%s", oldIngress.GetNamespace(), oldIngress.GetName()))

	if conditionFuncs == nil {
		conditionFuncs = []watch.ConditionFunc{isIngressAddedOrModified}
	}

	return k8s.waitForUpstreamIngress(updatedIngress, conditionFuncs...)
}

// GetService returns the service or an error.
func (k8s *K8sFramework) GetService(namespace, name string) (*coreV1.Service, error) {
	ctx := context.TODO()
	return k8s.CoreV1().Services(namespace).Get(ctx, name, metaV1.GetOptions{})
}

// UpdateServiceAndWait updates an existing Service and waits until the operation times out or is completed.
func (k8s *K8sFramework) UpdateServiceAndWait(oldService, newService *coreV1.Service, conditionFuncs ...watch.ConditionFunc) error {
	ctx := context.TODO()
	oldService, err := k8s.GetService(oldService.GetNamespace(), oldService.GetName())
	if err != nil {
		return err
	}

	// Nothing to update.
	if !isServiceNeedsUpdate(oldService, newService) {
		return nil
	}

	updatedService, err := k8s.CoreV1().Services(oldService.GetNamespace()).Update(ctx, newService, metaV1.UpdateOptions{})
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("updating service", "key", fmt.Sprintf("%s/%s", oldService.GetNamespace(), oldService.GetName()))

	if conditionFuncs == nil {
		conditionFuncs = []watch.ConditionFunc{isServiceAddedOrModified}
	}

	return k8s.waitForUpstreamService(updatedService, conditionFuncs...)
}

// GetDiscoRecord returns the Record or an error.
func (k8s *K8sFramework) GetDiscoRecord(namespace, name string) (*discov1.Record, error) {
	return k8s.DiscoCRDClientset.Records(namespace).Get(context.TODO(), name, metaV1.GetOptions{})
}

// UpdateDiscoRecordAndWait updates the given Record and waits until successfully completed or errored.
func (k8s *K8sFramework) UpdateDiscoRecordAndWait(oldDiscoRecord, newDiscoRecord *discov1.Record, conditionFuncs ...watch.ConditionFunc) error {
	ctx := context.TODO()
	oldDiscoRecord, err := k8s.GetDiscoRecord(oldDiscoRecord.GetNamespace(), oldDiscoRecord.GetName())
	if err != nil {
		return err
	}

	if !isDiscoRecordNeedsUpdate(oldDiscoRecord, newDiscoRecord) {
		return nil
	}

	updatedDiscoRecord, err := k8s.DiscoCRDClientset.Records(oldDiscoRecord.GetNamespace()).Update(ctx, newDiscoRecord)
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("updating discorecord", "key", fmt.Sprintf("%s/%s", oldDiscoRecord.GetNamespace(), oldDiscoRecord.GetName()))

	if conditionFuncs == nil {
		conditionFuncs = []watch.ConditionFunc{isDiscoRecordAddedOrModified}
	}

	return k8s.waitForUpstreamDiscoRecord(updatedDiscoRecord, conditionFuncs...)
}

// UpdateObjectAndWait updates an existing Ingress or Record and waits until the operation times out or is completed.
func (k8s *K8sFramework) UpdateObjectAndWait(oldObj, newObj runtime.Object, conditionFuncs ...watch.ConditionFunc) error {
	oldKind := oldObj.GetObjectKind().GroupVersionKind().Kind
	newKind := newObj.GetObjectKind().GroupVersionKind().Kind
	if oldKind != newKind {
		return fmt.Errorf("mismatching kind: %q vs %q", oldKind, newKind)
	}

	switch oldObj.(type) {
	case *extensionsv1beta1.Ingress:
		return k8s.UpdateIngressAndWait(oldObj.(*extensionsv1beta1.Ingress), newObj.(*extensionsv1beta1.Ingress), conditionFuncs...)
	case *coreV1.Service:
		return k8s.UpdateServiceAndWait(oldObj.(*coreV1.Service), newObj.(*coreV1.Service), conditionFuncs...)
	case *discov1.Record:
		return k8s.UpdateDiscoRecordAndWait(oldObj.(*discov1.Record), newObj.(*discov1.Record), conditionFuncs...)
	}

	return fmt.Errorf("unknown kind: %q", oldKind)
}

// EnsureDiscoFinalizerExists ensures the finalizer exists on the given object.
func (k8s *K8sFramework) EnsureDiscoFinalizerExists(obj runtime.Object) error {
	isHasDeletionTimestamp, err := HasDeletionTimestamp(obj)
	if err != nil {
		return err
	}

	// Add finalizer if not present and ingress was not deleted.
	if isHasDeletionTimestamp || hasDiscoFinalizer(obj, k8s.finalizer) {
		return nil
	}

	newObj := obj.DeepCopyObject()
	objMeta, err := meta.Accessor(obj)
	if err != nil {
		return err
	}

	finalizers := objMeta.GetFinalizers()
	if finalizers == nil {
		finalizers = []string{}
	}

	switch t := obj.(type) {
	case *extensionsv1beta1.Ingress:
		ing := newObj.(*extensionsv1beta1.Ingress)
		ing.Finalizers = append(finalizers, k8s.finalizer)
		newObj = ing

	case *coreV1.Service:
		svc := newObj.(*coreV1.Service)
		svc.Finalizers = append(finalizers, k8s.finalizer)
		newObj = svc

	case *discov1.Record:
		rec := newObj.(*discov1.Record)
		rec.Finalizers = append(finalizers, k8s.finalizer)
		newObj = rec

	default:
		return fmt.Errorf("unknown type: %q", t)
	}

	k8s.logger.LogDebug("adding finalizer", "key", fmt.Sprintf("%s/%s/%s", obj.GetObjectKind(), objMeta.GetNamespace(), objMeta.GetName()), "finalizer", k8s.finalizer)

	return k8s.UpdateObjectAndWait(
		obj, newObj,
		func(event apimachineryWatch.Event) (bool, error) {
			switch event.Type {
			case apimachineryWatch.Deleted:
				return false, apiErrors.NewNotFound(schema.GroupResource{Resource: obj.GetObjectKind().GroupVersionKind().Kind}, objMeta.GetName())
			}
			switch o := event.Object.(type) {
			case *extensionsv1beta1.Ingress, *coreV1.Service, *discov1.Record:
				return hasDiscoFinalizer(o, k8s.finalizer), nil
			}
			return false, nil
		},
	)
}

// EnsureDiscoFinalizerRemoved ensure the finalizer is removed from an existing Object.
func (k8s *K8sFramework) EnsureDiscoFinalizerRemoved(obj runtime.Object) error {
	isHasDeletionTimestamp, err := HasDeletionTimestamp(obj)
	if err != nil {
		return err
	}

	if hasDiscoFinalizer(obj, k8s.finalizer) && isHasDeletionTimestamp {
		newObj := obj.DeepCopyObject()

		objMeta, err := meta.Accessor(newObj)
		if err != nil {
			return err
		}

		finalizers := objMeta.GetFinalizers()
		for i, fin := range finalizers {
			if fin == k8s.finalizer {
				// Delete but preserve order of finalizers.
				finalizers = append(finalizers[:i], finalizers[i+1:]...)
			}
		}

		switch t := newObj.(type) {
		case *extensionsv1beta1.Ingress:
			ing := newObj.(*extensionsv1beta1.Ingress)
			ing.Finalizers = finalizers
			newObj = ing

		case *coreV1.Service:
			svc := newObj.(*coreV1.Service)
			svc.Finalizers = finalizers
			newObj = svc

		case *discov1.Record:
			rec := newObj.(*discov1.Record)
			rec.Finalizers = finalizers
			newObj = rec

		default:
			return fmt.Errorf("unknown type: %q", t)
		}

		k8s.logger.LogDebug("removing finalizer", "key", fmt.Sprintf("%s/%s/%s", obj.GetObjectKind(), objMeta.GetNamespace(), objMeta.GetName()), "finalizer", k8s.finalizer)

		return k8s.UpdateObjectAndWait(
			obj, newObj,
			func(event apimachineryWatch.Event) (bool, error) {
				switch event.Type {
				case apimachineryWatch.Deleted:
					return false, apiErrors.NewNotFound(schema.GroupResource{Resource: obj.GetObjectKind().GroupVersionKind().Kind}, objMeta.GetName())
				}
				switch ing := event.Object.(type) {
				case *extensionsv1beta1.Ingress, *coreV1.Service, *discov1.Record:
					return !hasDiscoFinalizer(ing, k8s.finalizer), nil
				}
				return false, nil
			},
		)
	}
	return nil
}

// waitForUpstreamIngress watches the given Ingress and wait for max. t minutes until the given condition applies.
func (k8s *K8sFramework) waitForUpstreamIngress(ingress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
	ctx, _ := context.WithTimeout(context.TODO(), WaitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metaV1.ListOptions) (object runtime.Object, e error) {
				return k8s.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).List(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: ingress.GetName()}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).Watch(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: ingress.GetName()}))
			},
		},
		ingress,
		nil,
		conditionFuncs...,
	)
	return err
}

// waitForUpstreamService watches the given Service and wait for max. t minutes until the given condition applies.
func (k8s *K8sFramework) waitForUpstreamService(service *coreV1.Service, conditionFuncs ...watch.ConditionFunc) error {
	ctx, _ := context.WithTimeout(context.TODO(), WaitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metaV1.ListOptions) (object runtime.Object, e error) {
				return k8s.CoreV1().Services(service.GetNamespace()).List(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: service.GetName()}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.CoreV1().Services(service.GetNamespace()).Watch(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: service.GetName()}))
			},
		},
		service,
		nil,
		conditionFuncs...,
	)
	return err
}

func (k8s *K8sFramework) waitForUpstreamDiscoRecord(discoRecord *discov1.Record, conditionFuncs ...watch.ConditionFunc) error {
	ctx, _ := context.WithTimeout(context.TODO(), WaitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metaV1.ListOptions) (object runtime.Object, e error) {
				return k8s.DiscoCRDClientset.Records(discoRecord.GetNamespace()).List(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: discoRecord.GetName()}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.DiscoCRDClientset.Records(discoRecord.GetNamespace()).Watch(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: discoRecord.GetName()}))
			},
		},
		discoRecord,
		nil,
		conditionFuncs...,
	)
	return err
}

func (k8s *K8sFramework) waitForUpstreamCRD(crd *extensionsobj.CustomResourceDefinition) error {
	ctx, _ := context.WithTimeout(context.TODO(), WaitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metaV1.ListOptions) (object runtime.Object, e error) {
				return k8s.CRDclientset.ApiextensionsV1beta1().CustomResourceDefinitions().List(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: crd.Name}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.CRDclientset.ApiextensionsV1beta1().CustomResourceDefinitions().Watch(ctx, metaV1.SingleObject(metaV1.ObjectMeta{Name: crd.Name}))
			},
		},
		crd,
		nil,
		isCRDAddedOrModified,
	)
	return err
}
