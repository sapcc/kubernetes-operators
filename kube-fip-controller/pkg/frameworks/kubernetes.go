/*******************************************************************************
*
* Copyright 2022 SAP SE
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

package frameworks

import (
	"context"
	"time"

	"github.com/go-kit/kit/log"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/config"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachinerywatch "k8s.io/apimachinery/pkg/watch"
	informersv1 "k8s.io/client-go/informers/core/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/tools/watch"
)

const (
	resyncPeriod = 5 * time.Minute
	waitTimeout  = 2 * time.Minute
)

// K8sFramework ..
type K8sFramework struct {
	*kubernetes.Clientset
	nodeInformer cache.SharedIndexInformer
	logger       log.Logger
}

// NewK8sFramework returns a new K8sFramework or an error.
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

	return &K8sFramework{
		Clientset:    clientset,
		logger:       log.With(logger, "component", "k8sFramework"),
		nodeInformer: informersv1.NewNodeInformer(clientset, resyncPeriod, cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc}),
	}, nil
}

// AddEventHandlerFuncsToNodeInformer adds EventHandlerFuncs to the node informer.
func (k8s *K8sFramework) AddEventHandlerFuncsToNodeInformer(addFunc, deleteFunc func(obj interface{}), updateFunc func(oldObj, newObj interface{})) {
	k8s.nodeInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    addFunc,
		UpdateFunc: updateFunc,
		DeleteFunc: deleteFunc,
	})
}

// Run starts the frameworks informers.
func (k8s *K8sFramework) Run(stopCh <-chan struct{}) {
	go k8s.nodeInformer.Run(stopCh)
}

// WaitForCacheToSync waits until all informer caches have been synced.
func (k8s *K8sFramework) WaitForCacheToSync(stopCh <-chan struct{}) bool {
	return cache.WaitForCacheSync(
		stopCh,
		k8s.nodeInformer.HasSynced,
	)
}

// GetNode gets a node by name and returns it or an error.
func (k8s *K8sFramework) GetNode(ctx context.Context, name string) (*corev1.Node, error) {
	return k8s.CoreV1().Nodes().Get(ctx, name, metav1.GetOptions{})
}

// AddLabelsToNode adds a set of labels to a node and waits until the operation is done or times out.
func (k8s *K8sFramework) AddLabelsToNode(ctx context.Context, node *corev1.Node, labels map[string]string) error {
	if labels == nil {
		return nil
	}

	oldNode, err := k8s.GetNode(ctx, node.GetName())
	if err != nil {
		return err
	}

	newNode := oldNode.DeepCopy()
	existingLabels := newNode.GetLabels()
	if existingLabels == nil {
		existingLabels = make(map[string]string)
	}

	for k, v := range labels {
		existingLabels[k] = v
	}
	newNode.SetLabels(existingLabels)

	updatedNode, err := k8s.CoreV1().Nodes().Update(ctx, newNode, metav1.UpdateOptions{})
	if err != nil {
		return err
	}

	return k8s.waitForNode(updatedNode, []watch.ConditionFunc{isNodeModified}...)
}

// GetNodeFromIndexerByKey returns a node by key from the informers indexer.
func (k8s *K8sFramework) GetNodeFromIndexerByKey(key string) (*corev1.Node, bool, error) {
	obj, exists, err := k8s.nodeInformer.GetIndexer().GetByKey(key)
	return obj.(*corev1.Node), exists, err
}

// GetNodeInformerStore returns the Store of the node informer.
func (k8s *K8sFramework) GetNodeInformerStore() cache.Store {
	return k8s.nodeInformer.GetStore()
}

func (k8s *K8sFramework) waitForNode(node *corev1.Node, conditionFuncs ...watch.ConditionFunc) error {
	ctx, _ := context.WithTimeout(context.TODO(), waitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metav1.ListOptions) (object runtime.Object, e error) {
				return k8s.CoreV1().Nodes().List(context.Background(), metav1.SingleObject(metav1.ObjectMeta{Name: node.GetName()}))
			},
			WatchFunc: func(options metav1.ListOptions) (i apimachinerywatch.Interface, e error) {
				return k8s.CoreV1().Nodes().Watch(context.Background(), metav1.SingleObject(metav1.ObjectMeta{Name: node.GetName()}))
			},
		},
		node,
		nil,
		conditionFuncs...,
	)
	return err
}

func isNodeModified(event apimachinerywatch.Event) (bool, error) {
	switch event.Type {
	case apimachinerywatch.Deleted:
		return false, apierrors.NewNotFound(schema.GroupResource{Resource: "node"}, "")
	case apimachinerywatch.Modified:
		return true, nil
	default:
		return false, nil
	}
}
