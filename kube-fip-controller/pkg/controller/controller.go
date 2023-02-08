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

package controller

import (
	"context"
	"errors"
	"reflect"
	"time"

	"github.com/go-kit/kit/log"
	"github.com/go-kit/kit/log/level"
	"github.com/gophercloud/gophercloud/openstack/compute/v2/servers"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/config"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/frameworks"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/metrics"
	corev1 "k8s.io/api/core/v1"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

const (
	// labelKubeFIPControllerEnabled whether the fip controller should handle the node.
	labelKubeFIPControllerEnabled = "kube-fip-controller.ccloud.sap.com/enabled"

	// labelExternalIP for storing the FIP assigned to the node.
	labelExternalIP = "kube-fip-controller.ccloud.sap.com/externalIP"

	// labelFloatingNetworkName controls which floating network is used for the FIP.
	labelFloatingNetworkName = "kube-fip-controller.ccloud.sap.com/floating-network-name"

	//labelFloatingSubnetName controls which floating subnet is used for the FIP.
	labelFloatingSubnetName = "kube-fip-controller.ccloud.sap.com/floating-subnet-name"

	// labelNodepoolName label used to identify nodepools
	labelNodepoolName = "ccloud.sap.com/nodepool"

	// labelReuseFIPs indicates if FIPs should be re-used for a certain nodepool
	labelReuseFIPs = "kube-fip-controller.ccloud.sap.com/reuse-fips"
)

// Controller ...
type Controller struct {
	opts         config.Options
	logger       log.Logger
	queue        workqueue.RateLimitingInterface
	k8sFramework *frameworks.K8sFramework
	osFramework  *frameworks.OSFramework
}

// New returns a new Controller or an error.
func New(opts config.Options, logger log.Logger) (*Controller, error) {
	authConfig, err := config.ReadAuthConfig(opts.ConfigPath)
	if err != nil {
		return nil, err
	}
	opts.Auth = authConfig

	k8sFramework, err := frameworks.NewK8sFramework(opts, logger)
	if err != nil {
		return nil, err
	}

	osFramework, err := frameworks.NewOSFramework(opts, logger)
	if err != nil {
		return nil, err
	}

	c := &Controller{
		opts:         opts,
		logger:       log.With(logger, "component", "controller"),
		queue:        workqueue.NewRateLimitingQueue(workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second)),
		k8sFramework: k8sFramework,
		osFramework:  osFramework,
	}

	c.k8sFramework.AddEventHandlerFuncsToNodeInformer(
		c.enqueueItem,
		c.enqueueItem,
		func(oldObj, newObj interface{}) {
			old := oldObj.(*corev1.Node)
			new := newObj.(*corev1.Node)
			if !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) || !reflect.DeepEqual(old.GetLabels(), new.GetLabels()) {
				c.enqueueItem(newObj)
			}
		},
	)
	return c, nil
}

// Run starts the Controller.
func (c *Controller) Run(threadiness int, stopCh <-chan struct{}) {
	defer utilruntime.HandleCrash()
	defer c.queue.ShutDown()

	level.Info(c.logger).Log("msg", "starting controller")

	c.k8sFramework.Run(stopCh)
	level.Info(c.logger).Log("msg", "waiting for caches to sync")

	if !c.k8sFramework.WaitForCacheToSync(stopCh) {
		utilruntime.HandleError(errors.New("timed out while waiting for informer caches to sync"))
		return
	}

	for i := 0; i < threadiness; i++ {
		go wait.Until(c.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(c.opts.RecheckInterval)
	go func() {
		for {
			select {
			case <-ticker.C:
				c.enqueueAllItems()
				level.Info(c.logger).Log("msg", "completed another cycle", "interval", c.opts.RecheckInterval.String())
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
	level.Info(c.logger).Log("msg", "stopping controller")
}

func (c *Controller) runWorker() {
	for c.processNextItem() {
	}
}

func (c *Controller) processNextItem() bool {
	key, quit := c.queue.Get()
	if quit {
		return false
	}

	defer c.queue.Done(key)

	err := c.syncHandler(key.(string))
	c.handleError(err, key)
	return true
}

func (c *Controller) syncHandler(key string) error {
	ctx := context.Background()

	node, exists, err := c.k8sFramework.GetNodeFromIndexerByKey(key)
	if err != nil {
		level.Error(c.logger).Log("msg", "failed to get object from store", "err", err)
		return err
	}

	if !exists {
		level.Debug(c.logger).Log("msg", "node does not exist anymore", "key", key)
		return nil
	}

	// Ignore the node if enable label is not set.
	val, ok := getLabelValue(node, labelKubeFIPControllerEnabled)
	if !ok || val != "true" {
		level.Debug(c.logger).Log("msg", "ignoring node as label not set", "node", node.GetName(), "label", labelKubeFIPControllerEnabled)
		return nil
	}

	floatingNetworkName := c.opts.DefaultFloatingNetwork
	if val, ok := getLabelValue(node, labelFloatingNetworkName); ok && val != "" {
		floatingNetworkName = val
	}

	floatingNetworkID, err := c.osFramework.GetNetworkIDByName(floatingNetworkName)
	if err != nil {
		return err
	}

	floatingSubnetName := c.opts.DefaultFloatingSubnet
	if val, ok := getLabelValue(node, labelFloatingSubnetName); ok && val != "" {
		floatingSubnetName = val
	}

	floatingSubnetID, err := c.osFramework.GetSubnetIDByName(floatingSubnetName)
	if err != nil {
		return err
	}

	floatingIP := ""
	if val, ok := getLabelValue(node, labelExternalIP); ok {
		floatingIP = val
	}

	server, err := c.getServer(node)
	if err != nil {
		return err
	}

	nodepool := ""
	if val, ok := getLabelValue(node, labelNodepoolName); ok {
		nodepool = val
	}

	reuseFIPs := false
	if val, ok := getLabelValue(node, labelReuseFIPs); ok {
		reuseFIPs = (val == "true")
	}

	fip, err := c.osFramework.GetOrCreateFloatingIP(floatingIP, floatingNetworkID, floatingSubnetID, server.TenantID, nodepool, reuseFIPs)
	if err != nil {
		return err
	}

	// Add the FIP to the node as label.
	err = c.k8sFramework.AddLabelsToNode(
		ctx, node,
		map[string]string{
			labelExternalIP: fip.FloatingIP,
		},
	)
	if err != nil {
		return err
	}

	return c.osFramework.EnsureAssociatedInstanceAndFIP(server, fip)
}

func (c *Controller) handleError(err error, key interface{}) {
	if err == nil {
		metrics.MetricSuccessfulOperations.Inc()
		c.queue.Forget(key)
		return
	}
	metrics.MetricFailedOperations.Inc()

	if c.queue.NumRequeues(key) < 5 {
		level.Info(c.logger).Log("msg", "error syncing key", "key", key, "err", err)
		c.queue.AddRateLimited(key)
		return
	}

	c.queue.Forget(key)
	utilruntime.HandleError(err)
	level.Info(c.logger).Log("msg", "dropping from queue", "key", key, "err", err)
}

func (c *Controller) enqueueItem(obj interface{}) {
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		utilruntime.HandleError(err)
		return
	}
	c.queue.AddRateLimited(key)
}

func (c *Controller) enqueueAllItems() {
	for _, obj := range c.k8sFramework.GetNodeInformerStore().List() {
		c.enqueueItem(obj)
	}
}

func (c *Controller) getServer(node *corev1.Node) (*servers.Server, error) {
	if serverID, err := getServerIDFromNode(node); err == nil {
		if server, err := c.osFramework.GetServerByID(serverID); err == nil {
			return server, nil
		}
	}

	return c.osFramework.GetServerByName(node.GetName())
}
