package controller

import (
	"errors"
	"reflect"
	"time"

	"github.com/go-kit/kit/log"
	"github.com/go-kit/kit/log/level"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/config"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/frameworks"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/metrics"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/meta"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

const (
	// annotationKubeFIPControllerEnabled whether the fip controller should handle the node.
	annotationKubeFIPControllerEnabled = "kube-fip-controller.ccloud.sap.com/enabled"

	// annotationExternalIPFIP for storing the FIP assigned to the node.
	annotationExternalIPFIP = "kube-fip-controller.ccloud.sap.com/fip"

	// annotationFloatingNetworkName controls which floating network is used for the FIP.
	annotationFloatingNetworkName = "kube-fip-controller.ccloud.sap.com/floating-network-name"

	//annotationFloatingSubnetName controls which floating subnet is used for the FIP.
	annotationFloatingSubnetName = "kube-fip-controller.ccloud.sap.com/floating-subnet-name"

	// labelKubernikusNodePool is used to determine whether a node is part of a node pool.
	labelKubernikusNodePool = "ccloud.sap.com/nodepool"
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
	opts.Auth = *authConfig

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
			if !reflect.DeepEqual(old.GetAnnotations(), new.GetAnnotations()) {
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
	node, exists, err := c.k8sFramework.GetNodeFromIndexerByKey(key)
	if err != nil {
		level.Error(c.logger).Log("msg", "failed to get object from store", "err", err)
		return err
	}

	if !exists {
		level.Debug(c.logger).Log("msg", "node does not exist anymore", "key", key)
		return nil
	}

	// Ignore the node if enable annotation is not set.
	val, ok := getAnnotationValue(node, annotationKubeFIPControllerEnabled)
	if !ok || val != "true" {
		level.Debug(c.logger).Log("msg", "ignoring node as annotation not set", "node", node.GetName(), "annotation", annotationKubeFIPControllerEnabled)
		return nil
	}

	floatingNetworkName := c.opts.DefaultFloatingNetwork
	if val, ok := getAnnotationValue(node, annotationFloatingNetworkName); ok && val != "" {
		floatingNetworkName = val
	}

	floatingNetworkID, err := c.osFramework.GetNetworkIDByName(floatingNetworkName)
	if err != nil {
		return err
	}

	floatingSubnetName := c.opts.DefaultFloatingSubnet
	if val, ok := getAnnotationValue(node, annotationFloatingSubnetName); ok && val != "" {
		floatingSubnetName = val
	}

	floatingSubnetID, err := c.osFramework.GetSubnetIDByName(floatingSubnetName)
	if err != nil {
		return err
	}

	floatingIP := ""
	if val, ok := getAnnotationValue(node, annotationExternalIPFIP); ok {
		floatingIP = val
	}

	fip, err := c.osFramework.GetOrCreateFloatingIP(floatingIP, floatingNetworkID, floatingSubnetID)
	if err != nil {
		return err
	}

	// Add the FIP to the node as annotation.
	err = c.k8sFramework.AddAnnotationsToNode(
		node,
		map[string]string{
			annotationExternalIPFIP: fip.FloatingIP,
		},
	)
	if err != nil {
		return err
	}

	server, err := c.osFramework.GetServerByName(node.GetName())
	if err != nil {
		return err
	}

	err = c.osFramework.EnsureAssociatedInstanceAndFIP(server, fip)
	if err == nil {
		metrics.MetricSuccessfulOperations.Inc()
	}
	return err
}

func (c *Controller) handleError(err error, key interface{}) {
	if err == nil {
		c.queue.Forget(key)
		return
	}

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

func getAnnotationValue(obj interface{}, annKey string) (string, bool) {
	objMeta, err := meta.Accessor(obj)
	if err != nil {
		return "", false
	}

	ann := objMeta.GetAnnotations()
	if ann == nil {
		ann = make(map[string]string, 0)
	}

	val, ok := ann[annKey]
	return val, ok
}