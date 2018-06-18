/*
Copyright 2017 SAP SE

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
package controller

import (
	"fmt"
	"gopkg.in/yaml.v2"
	"time"

	"github.com/golang/glog"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	typedcorev1 "k8s.io/client-go/kubernetes/typed/core/v1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/util/workqueue"

	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apierrors "k8s.io/apimachinery/pkg/api/errors"

	"flag"
	"github.com/getsentry/raven-go"
	seederv1 "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/apis/seeder/v1"
	clientset "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/client/clientset/versioned"
	seederscheme "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/client/clientset/versioned/scheme"
	informers "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/client/informers/externalversions/seeder/v1"
	listers "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/client/listers/seeder/v1"
	"os"
	"os/exec"
)

const controllerAgentName = "openstack-seeder-controller"

const (
	// SuccessSynced is used as part of the Event 'reason' when a OpenstackSeed is synced
	SuccessSynced = "Synced"
	// MessageResourceSynced is the message used for an Event fired when a OpenstackSeed
	// is synced successfully
	MessageResourceSynced = "OpenstackSeed seeded successfully"
)

var (
	VERSION = "0.1.0.dev"
)

type Options struct {
	MasterURL     string
	KubeConfig    string
	DryRun        bool
	InterfaceType string
	ResyncPeriod  time.Duration
}

// Controller is the controller implementation for OpenstackSeed resources
type Controller struct {
	Options

	// kubeclientset is a standard kubernetes clientset
	kubeclientset kubernetes.Interface
	// seederclientset is a clientset for our own API group
	seederclientset        clientset.Interface
	apiextensionsclientset apiextensionsclient.Interface

	openstackseedsLister listers.OpenstackSeedLister
	openstackseedsSynced cache.InformerSynced

	// workqueue is a rate limited work queue. This is used to queue work to be
	// processed instead of performing it as soon as a change happens. This
	// means we can ensure we only process a fixed amount of resources at a
	// time, and makes it easy to ensure we are never processing the same item
	// simultaneously in two different workers.
	workqueue workqueue.RateLimitingInterface
	// recorder is an event recorder for recording Event resources to the
	// Kubernetes API.
	recorder record.EventRecorder
}

// NewController returns a new OpenstackSeed controller
func NewController(
	options Options,
	kubeclientset kubernetes.Interface,
	apiextensionsclientset apiextensionsclient.Interface,
	seederclientset clientset.Interface,
	openstackseedInformer informers.OpenstackSeedInformer) *Controller {
	glog.Infof("Creating new OpenstackSeederController in version %v", VERSION)

	// initialize custom resource using a CustomResourceDefinition if it does not exist
	_, err := CreateCustomResourceDefinition(apiextensionsclientset)
	if err != nil && !apierrors.IsAlreadyExists(err) {
		glog.Fatalf("Couldn't create OpenstackSeed CRD: %v", err)
	}

	// Create event broadcaster
	// Add openstackseed-controller types to the default Kubernetes Scheme so Events can be
	// logged for openstackseed-controller types.
	seederscheme.AddToScheme(scheme.Scheme)
	glog.Info("Creating event broadcaster")
	eventBroadcaster := record.NewBroadcaster()
	eventBroadcaster.StartLogging(glog.Infof)
	eventBroadcaster.StartRecordingToSink(&typedcorev1.EventSinkImpl{Interface: kubeclientset.CoreV1().Events("")})
	recorder := eventBroadcaster.NewRecorder(scheme.Scheme, corev1.EventSource{Component: controllerAgentName})

	controller := &Controller{
		Options:                options,
		kubeclientset:          kubeclientset,
		seederclientset:        seederclientset,
		apiextensionsclientset: apiextensionsclientset,
		openstackseedsLister:   openstackseedInformer.Lister(),
		openstackseedsSynced:   openstackseedInformer.Informer().HasSynced,
		workqueue:              workqueue.NewNamedRateLimitingQueue(workqueue.DefaultControllerRateLimiter(), "OpenstackSeeds"),
		recorder:               recorder,
	}

	glog.Info("Setting up event handlers")
	// Set up an event handler for when OpenstackSeed resources change
	openstackseedInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.enqueueOpenstackSeed,
		UpdateFunc: func(old, new interface{}) {
			controller.enqueueOpenstackSeed(new)
		},
	})
	return controller
}

// Run will set up the event handlers for types we are interested in, as well
// as syncing informer caches and starting workers. It will block until stopCh
// is closed, at which point it will shutdown the workqueue and wait for
// workers to finish processing their current work items.
func (c *Controller) Run(threadiness int, stopCh <-chan struct{}) error {
	defer runtime.HandleCrash()
	defer c.workqueue.ShutDown()

	// Start the informer factories to begin populating the informer caches
	glog.Info("Starting OpenstackSeed controller")

	// Wait for the caches to be synced before starting workers
	glog.Info("Waiting for informer caches to sync")
	if ok := cache.WaitForCacheSync(stopCh, c.openstackseedsSynced); !ok {
		return fmt.Errorf("failed to wait for caches to sync")
	}

	glog.Info("Starting workers")
	// Launch two workers to process OpenstackSeed resources
	for i := 0; i < threadiness; i++ {
		go wait.Until(c.runWorker, time.Second, stopCh)
	}

	glog.Info("Started workers")
	<-stopCh
	glog.Info("Shutting down workers")

	return nil
}

// runWorker is a long-running function that will continually call the
// processNextWorkItem function in order to read and process a message on the
// workqueue.
func (c *Controller) runWorker() {
	for c.processNextWorkItem() {
	}
}

// processNextWorkItem will read a single work item off the workqueue and
// attempt to process it, by calling the seedHandler.
func (c *Controller) processNextWorkItem() bool {
	obj, shutdown := c.workqueue.Get()

	if shutdown {
		return false
	}

	// We wrap this block in a func so we can defer c.workqueue.Done.
	err := func(obj interface{}) error {
		// We call Done here so the workqueue knows we have finished
		// processing this item. We also must remember to call Forget if we
		// do not want this work item being re-queued. For example, we do
		// not call Forget if a transient error occurs, instead the item is
		// put back on the workqueue and attempted again after a back-off
		// period.
		defer c.workqueue.Done(obj)
		var key string
		var ok bool
		// We expect strings to come off the workqueue. These are of the
		// form namespace/name. We do this as the delayed nature of the
		// workqueue means the items in the informer cache may actually be
		// more up to date that when the item was initially put onto the
		// workqueue.
		if key, ok = obj.(string); !ok {
			// As the item in the workqueue is actually invalid, we call
			// Forget here else we'd go into a loop of attempting to
			// process a work item that is invalid.
			c.workqueue.Forget(obj)
			runtime.HandleError(fmt.Errorf("expected string in workqueue but got %#v", obj))
			return nil
		}
		// Run the seedHandler, passing it the namespace/name string of the
		// OpenstackSeed resource to be synced.
		if err := c.seedHandler(key); err != nil {
			// drop from queue, since it has an issue and can't be processed
			c.workqueue.Forget(obj)
			return fmt.Errorf("error syncing '%s': %s", key, err.Error())
		}
		// Finally, if no error occurs we Forget this item so it does not
		// get queued again until another change happens.
		c.workqueue.Forget(obj)
		glog.V(2).Infof("Successfully synced '%s'", key)
		return nil
	}(obj)

	if err != nil {
		runtime.HandleError(err)
		return true
	}

	return true
}

// seedHandler compares the actual state with the desired, and attempts to
// converge the two. It then updates the Status block of the OpenstackSeed resource
// with the current status of the resource.
func (c *Controller) seedHandler(key string) error {
	const seeder_name string = "openstack-seed-loader"

	glog.V(2).Infof("Processing %s ..", key)

	// Convert the namespace/name string into a distinct namespace and name
	namespace, name, err := cache.SplitMetaNamespaceKey(key)
	if err != nil {
		runtime.HandleError(fmt.Errorf("invalid resource key: %s", key))
		return nil
	}

	// Get the OpenstackSeed resource with this namespace/name
	seed, err := c.openstackseedsLister.OpenstackSeeds(namespace).Get(name)
	if err != nil {
		// The OpenstackSeed resource may no longer exist, in which case we stop
		// processing.
		if errors.IsNotFound(err) {
			runtime.HandleError(fmt.Errorf("seed '%s' in work queue no longer exists", key))
			return nil
		}

		return err
	}

	if seed.Status == nil {
		seed.Status = &seederv1.OpenstackSeedStatus{Processed: ""}
	}

	if seed.Status.Processed != "" {
		glog.V(2).Infof("Seed %s/%s has been seeded on %v. Skipping..", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, seed.Status.Processed)
		return nil
	}

	result := &seederv1.OpenstackSeed{ObjectMeta: seed.ObjectMeta, Status: seed.Status}

	err = c.resolveSeedDependencies(result, seed)

	if err != nil {
		msg := fmt.Errorf("failed to process openstackseed '%s/%s': %s", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, err.Error())
		raven.CaptureError(msg, nil)
		glog.Errorf("ERROR: %s", msg.Error())
		return err
	}

	yaml_seed, _ := yaml.Marshal(result.Spec)

	glog.V(1).Infof("Seeding %s/%s ..", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name)

	// spawn a python keystone-seeder as long as there is no functional golang keystone client
	_, err = exec.LookPath(seeder_name)
	if err != nil {
		glog.Errorf("ERROR: python %s not found.", seeder_name)
		return err
	}

	level := "ERROR"
	switch flag.Lookup("v").Value.String() {
	case "0":
		level = "WARNING"
	case "1":
		level = "INFO"
	default:
		level = "DEBUG"
	}

	cmd := exec.Command(seeder_name, "--interface", c.Options.InterfaceType, "-l", level)
	if c.Options.DryRun {
		cmd = exec.Command(seeder_name, "--interface", c.Options.InterfaceType, "-l", level, "--dry-run")
	}

	// inherit the os-environment
	env := os.Environ()
	cmd.Env = env

	glog.V(2).Infof("Spawning %s, args: %s, env: %s", cmd.Path, cmd.Args, cmd.Env)

	stdin, err := cmd.StdinPipe()
	if err != nil {
		glog.Error(err)
	}

	defer stdin.Close()

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err = cmd.Start(); err != nil {
		glog.Errorf("ERROR: could not spawn %s: ", seeder_name, err)
	}

	stdin.Write(yaml_seed)
	stdin.Close()
	if err := cmd.Wait(); err != nil {
		msg := fmt.Errorf("failed to seed '%s/%s': %s", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, err.Error())
		raven.CaptureError(msg, nil)
		glog.Errorf("ERROR: %s", msg.Error())
		return err
	}

	glog.Infof("Seeding %s/%s done.", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name)

	// Finally, we update the status block of the OpenstackSeed resource to reflect the
	// current state of the world
	//TODO: uncomment once bug has been fixed
	// https://github.com/coreos/prometheus-operator/issues/1293
	//err = c.updateOpenstackSeedStatus(result, time.Now())
	//if err != nil {
	//	return err
	//}

	c.recorder.Event(seed, corev1.EventTypeNormal, SuccessSynced, MessageResourceSynced)
	return nil
}

func (c *Controller) updateOpenstackSeedStatus(seed *seederv1.OpenstackSeed, lastSeeded time.Time) error {
	// NEVER modify objects from the store. It's a read-only, local cache.
	// You can use DeepCopy() to make a deep copy of original object and modify this copy
	// Or create a copy manually for better performance
	seedCopy := seed.DeepCopy()
	seedCopy.Status.Processed = lastSeeded.Format(time.RFC3339)
	// If the CustomResourceSubresources feature gate is not enabled,
	// we must use Update instead of UpdateStatus to update the Status block of the OpenstackSeed resource.
	// UpdateStatus will not allow changes to the Spec of the resource,
	// which is ideal for ensuring nothing other than resource status has been updated.
	_, err := c.seederclientset.OpenstackV1().OpenstackSeeds(seed.Namespace).UpdateStatus(seedCopy)
	return err
}

// enqueueOpenstackSeed takes a OpenstackSeed resource and converts it into a namespace/name
// string which is then put onto the work queue. This method should *not* be
// passed resources of any type other than OpenstackSeed.
func (c *Controller) enqueueOpenstackSeed(obj interface{}) {
	var key string
	var err error
	if key, err = cache.MetaNamespaceKeyFunc(obj); err != nil {
		runtime.HandleError(err)
		return
	}
	c.workqueue.AddRateLimited(key)
}

func (c *Controller) resolveSeedDependencies(result *seederv1.OpenstackSeed, seed *seederv1.OpenstackSeed) (err error) {
	if result.Status == nil {
		result.Status = &seederv1.OpenstackSeedStatus{Processed: ""}
	}

	if result.Status.VisitedDependencies == nil {
		result.Status.VisitedDependencies = make(map[string]bool)
	}

	var name = seed.ObjectMeta.Namespace + "/" + seed.ObjectMeta.Name

	if result.Status.VisitedDependencies[name] {
		// visited already, skip now
		return nil
	}

	if len(seed.Spec.Dependencies) > 0 {
		for _, v := range seed.Spec.Dependencies {
			var spec *seederv1.OpenstackSeed

			// Convert the namespace/name string into a distinct namespace and name
			namespace, name, err := cache.SplitMetaNamespaceKey(v)
			if namespace == "" {
				namespace = seed.ObjectMeta.Namespace
			}
			spec, err = c.openstackseedsLister.OpenstackSeeds(namespace).Get(name)
			if err != nil {
				msg := fmt.Errorf("dependency '%s/%s' of '%s/%s' not found", namespace, name, seed.ObjectMeta.Namespace, seed.ObjectMeta.Name)
				raven.CaptureError(msg, nil)
				glog.Errorf("ERROR: %s", msg.Error())
				return err
			}
			glog.Infof("Processing dependency '%s' of '%s'.", v, name)
			err = c.resolveSeedDependencies(result, spec)
			if err != nil {
				return err
			}
		}
	}
	result.Status.VisitedDependencies[name] = true
	err = result.Spec.MergeSpec(seed.Spec)
	return err
}
