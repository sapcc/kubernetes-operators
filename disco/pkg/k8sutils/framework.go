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

	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
	genCRDClientset "github.com/sapcc/kubernetes-operators/disco/pkg/generated/clientset/versioned"
	discoClientV1 "github.com/sapcc/kubernetes-operators/disco/pkg/generated/clientset/versioned/typed/disco.stable.sap.cc/v1"
	genCRDInformers "github.com/sapcc/kubernetes-operators/disco/pkg/generated/informers/externalversions"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
	coreV1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	extensionsobj "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1beta1"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	apimetav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachineryWatch "k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	v12 "k8s.io/client-go/kubernetes/typed/core/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/tools/watch"
)

// WaitTimeout
const WaitTimeout = 2 * time.Minute

// K8sFramework ..
type K8sFramework struct {
	*kubernetes.Clientset
	logger        log.Logger
	kubeConfig    *rest.Config
	eventRecorder record.EventRecorder

	CRDclientset      *apiextensionsclient.Clientset
	DiscoCRDClientset *discoClientV1.DiscoV1Client
}

// NewK8sFramework ...
func NewK8sFramework(options disco.Options, logger log.Logger) (*K8sFramework, error) {
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

	b := record.NewBroadcaster()
	b.StartLogging(logger.LogEvent)
	b.StartRecordingToSink(&v12.EventSinkImpl{
		Interface: clientset.CoreV1().Events(apimetav1.NamespaceNone),
	})
	eventRecorder := b.NewRecorder(scheme.Scheme, coreV1.EventSource{
		Component: options.EventComponent,
	})

	return &K8sFramework{
		Clientset:         clientset,
		kubeConfig:        config,
		eventRecorder:     eventRecorder,
		CRDclientset:      crdclientset,
		DiscoCRDClientset: discoCRDClient,
		logger:            log.NewLoggerWith(logger, "component", "k8sFramework"),
	}, nil
}

func (k8s *K8sFramework) NewDiscoCRDInformerWithResyncPeriod(resyncPeriod time.Duration) (cache.SharedIndexInformer, error) {
	c, err := genCRDClientset.NewForConfig(k8s.kubeConfig)
	if err != nil {
		return nil, err
	}
	infFactory := genCRDInformers.NewSharedInformerFactory(c, resyncPeriod)
	return infFactory.Disco().V1().DiscoRecords().Informer(), nil
}

// Eventf emits an event via the event recorder.
func (k8s *K8sFramework) Eventf(object runtime.Object, eventType, reason, messageFmt string, args ...interface{}) {
	k8s.eventRecorder.Eventf(object, eventType, reason, messageFmt)
}

func (k8s *K8sFramework) CreateDiscoRecordCRDAndWaitUntilReady() error {
	crd := NewDiscoRecordCRD()
	crdClient := k8s.CRDclientset.ApiextensionsV1beta1().CustomResourceDefinitions()
	oldCRD, err := crdClient.Get(crd.Name, metaV1.GetOptions{})
	if err != nil && apiErrors.IsNotFound(err) {
		if _, err := crdClient.Create(crd); err != nil {
			return err
		}
	}
	if crd.ResourceVersion != oldCRD.ResourceVersion {
		if _, err := crdClient.Update(crd); err != nil {
			return err
		}
	}

	return k8s.waitForUpstreamCRD(crd)
}

// GetIngress returns the ingress or an error.
func (k8s *K8sFramework) GetIngress(namespace, name string) (*extensionsv1beta1.Ingress, error) {
	return k8s.ExtensionsV1beta1().Ingresses(namespace).Get(name, metaV1.GetOptions{})
}

// UpdateIngressAndWait updates an existing Ingress and waits until the operation times out or is completed.
func (k8s *K8sFramework) UpdateIngressAndWait(oldIngress, newIngress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
	oldIngress, err := k8s.ExtensionsV1beta1().Ingresses(oldIngress.GetNamespace()).Get(oldIngress.GetName(), metaV1.GetOptions{})
	if err != nil {
		return err
	}

	// Nothing to update.
	if !isIngressNeedsUpdate(oldIngress, newIngress) {
		return nil
	}

	updatedIngress, err := k8s.ExtensionsV1beta1().Ingresses(oldIngress.GetNamespace()).Update(newIngress)
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("updating ingress", "ingress", fmt.Sprintf("%s/%s", oldIngress.GetNamespace(), oldIngress.GetName()))

	if conditionFuncs == nil {
		conditionFuncs = []watch.ConditionFunc{isIngressAddedOrModified}
	}

	return k8s.waitForUpstreamIngress(updatedIngress, conditionFuncs...)
}

func (k8s *K8sFramework) EnsureDiscoFinalizerExists(ingress *extensionsv1beta1.Ingress) error {
	// Add finalizer if not present and ingress was not deleted.
	if !ingressHasDiscoFinalizer(ingress) && !ingressHasDeletionTimestamp(ingress) {
		newIngress := ingress.DeepCopy()
		newIngress.Finalizers = append(newIngress.GetFinalizers(), disco.DiscoFinalizer)

		k8s.logger.LogDebug("adding finalizer to ingress", "ingress", fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName()), "finalizer", disco.DiscoFinalizer)

		return k8s.UpdateIngressAndWait(
			ingress, newIngress,
			func(event apimachineryWatch.Event) (bool, error) {
				switch event.Type {
				case apimachineryWatch.Deleted:
					return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
				}
				switch ing := event.Object.(type) {
				case *extensionsv1beta1.Ingress:
					return ingressHasDiscoFinalizer(ing), nil
				}
				return false, nil
			},
		)
	}
	return nil
}

func (k8s *K8sFramework) EnsureDiscoFinalizerRemoved(ingress *extensionsv1beta1.Ingress) error {
	// Do not remove finalizer if DeletionTimestamp is not set.
	if ingressHasDiscoFinalizer(ingress) && ingressHasDeletionTimestamp(ingress) {
		newIngress := ingress.DeepCopy()
		for i, fin := range newIngress.GetFinalizers() {
			if fin == disco.DiscoFinalizer {
				// Delete but preserve order.
				newIngress.Finalizers = append(newIngress.Finalizers[:i], newIngress.Finalizers[i+1:]...)

				k8s.logger.LogDebug("removing finalizer from ingress", "ingress", fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName()), "finalizer", disco.DiscoFinalizer)

				return k8s.UpdateIngressAndWait(
					ingress, newIngress,
					func(event apimachineryWatch.Event) (bool, error) {
						switch event.Type {
						case apimachineryWatch.Deleted:
							return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
						}
						switch ing := event.Object.(type) {
						case *extensionsv1beta1.Ingress:
							return !ingressHasDiscoFinalizer(ing), nil
						}
						return false, nil
					},
				)
			}
		}
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
				return k8s.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).List(metaV1.SingleObject(metaV1.ObjectMeta{Name: ingress.GetName()}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).Watch(metaV1.SingleObject(metaV1.ObjectMeta{Name: ingress.GetName()}))
			},
		},
		ingress,
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
				return k8s.CRDclientset.ApiextensionsV1beta1().CustomResourceDefinitions().List(metaV1.SingleObject(metaV1.ObjectMeta{Name: crd.Name}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.CRDclientset.ApiextensionsV1beta1().CustomResourceDefinitions().Watch(metaV1.SingleObject(metaV1.ObjectMeta{Name: crd.Name}))
			},
		},
		crd,
		nil,
		isCRDAddedOrModified,
	)
	return err
}
