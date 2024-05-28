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
	"context"
	"flag"
	"slices"

	"gopkg.in/yaml.v2"

	"k8s.io/apimachinery/pkg/fields"
	"k8s.io/apimachinery/pkg/runtime"
	apiv1 "k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"

	seederv1 "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/apis/v1"
	seederclient "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/client"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apierrors "k8s.io/apimachinery/pkg/api/errors"

	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/getsentry/raven-go"
	"github.com/golang/glog"
	"k8s.io/client-go/tools/clientcmd"
)

var (
	VERSION      = "0.0.1.dev"
	resyncPeriod = 5 * time.Minute
)

type Options struct {
	KubeConfig       string
	DryRun           bool
	InterfaceType    string
	IgnoreNamespaces []string
	OnlyNamespaces   []string
}

type SeederController struct {
	Options
	SeederClient *rest.RESTClient
	SeederScheme *runtime.Scheme
	seedInformer cache.SharedIndexInformer
}

// New creates a new operator using the given options
func New(options Options) *SeederController {

	glog.Infof("Creating new OpenstackSeederController in version %v", VERSION)

	// Create the client config. Use kubeconfig if given, otherwise assume in-cluster.
	config, err := buildConfig(options.KubeConfig)
	if err != nil {
		glog.Fatalf("Couldn't create config: %v", err)
	}

	apiextensionsclientset, err := apiextensionsclient.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create api-extension-client: %v", err)
	}

	// initialize custom resource using a CustomResourceDefinition if it does not exist
	_, err = seederclient.CreateCustomResourceDefinition(apiextensionsclientset)
	if err != nil && !apierrors.IsAlreadyExists(err) {
		glog.Fatalf("Couldn't create OpenstackSeed CRD: %v", err)
	}

	// make a new config for our extension's API group, using the first config as a baseline
	seederClient, seederScheme, err := seederclient.NewClient(config)
	if err != nil {
		glog.Fatalf("Couldn't create client: %v", err)
	}

	// start a controller on instances of our custom resource
	controller := &SeederController{
		Options:      options,
		SeederClient: seederClient,
		SeederScheme: seederScheme,
	}

	return controller
}

func buildConfig(kubeconfig string) (*rest.Config, error) {
	if kubeconfig != "" {
		return clientcmd.BuildConfigFromFlags("", kubeconfig)
	}
	return rest.InClusterConfig()
}

// Run starts an OpenstackSeed resource controller
func (c *SeederController) Run(ctx context.Context) error {
	glog.Info("Running OpenstackSeeder controller")

	// Watch OpenstackSeed objects
	_, err := c.watchOpenstackSeeds(ctx)
	if err != nil {
		glog.Errorf("Failed to register watcher for OpenstackSeed resource: %v", err)
		return err
	}

	<-ctx.Done()
	return ctx.Err()
}

func (c *SeederController) watchOpenstackSeeds(ctx context.Context) (cache.Controller, error) {
	source := cache.NewListWatchFromClient(
		c.SeederClient,
		seederv1.OpenstackSeedResourcePlural,
		apiv1.NamespaceAll,
		fields.Everything())

	informer := cache.NewSharedIndexInformer(
		source,
		// The object type.
		&seederv1.OpenstackSeed{},
		// resyncPeriod
		// Every resyncPeriod, all resources in the cache will retrigger events.
		// Set to 0 to disable the resync.
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	// Your custom resource event handlers.
	informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    c.onAdd,
		UpdateFunc: c.onUpdate,
		DeleteFunc: c.onDelete,
	})

	c.seedInformer = informer
	go informer.Run(ctx.Done())
	return informer, nil
}

func (c *SeederController) onAdd(obj interface{}) {
	seed := obj.(*seederv1.OpenstackSeed)
	// NEVER modify objects from the store. It's a read-only, local cache.
	// You can use Scheme.Copy() to make a deep copy of original object and modify this copy
	// Or create a copy manually for better performance
	copyObj, err := c.SeederScheme.Copy(seed)
	if err != nil {
		glog.Errorf("ERROR creating a deep copy of openstackseed object: %v", err)
		return
	}

	seedCopy := copyObj.(*seederv1.OpenstackSeed)

	if seedCopy.ObjectMeta.Name != "" {
		glog.Infof("Added %s/%s - version: %s", seedCopy.ObjectMeta.Namespace, seedCopy.ObjectMeta.Name, seedCopy.ObjectMeta.ResourceVersion)
		c.seedApply(seedCopy)
	}
}

func (c *SeederController) onUpdate(oldObj, newObj interface{}) {
	oldSeed := oldObj.(*seederv1.OpenstackSeed)
	newSeed := newObj.(*seederv1.OpenstackSeed)

	if newSeed.ObjectMeta.Name != "" {
		if newSeed.ObjectMeta.ResourceVersion == oldSeed.ObjectMeta.ResourceVersion {
			return
		}
		glog.Infof("Updated %s/%s - version: %s", newSeed.ObjectMeta.Namespace, newSeed.ObjectMeta.Name, newSeed.ObjectMeta.ResourceVersion)
		copyObj, err := c.SeederScheme.Copy(newSeed)
		if err != nil {
			glog.Errorf("ERROR creating a deep copy of openstackseed object: %v", err)
			return
		}
		seedCopy := copyObj.(*seederv1.OpenstackSeed)
		c.seedApply(seedCopy)
	}

}

func (c *SeederController) onDelete(obj interface{}) {
	seed := obj.(*seederv1.OpenstackSeed)
	glog.Infof("Deleted %s/%s - version: %s", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, seed.ObjectMeta.ResourceVersion)
}

func (c *SeederController) seedApply(seed *seederv1.OpenstackSeed) {
	const seeder_name string = "openstack-seed-loader"
	result := new(seederv1.OpenstackSeed)
	result.ObjectMeta = seed.ObjectMeta
	err := c.resolveSeedDependencies(result, seed)

	if err != nil {
		msg := fmt.Errorf("failed to process openstackseed '%s/%s': %s", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, err.Error())
		raven.CaptureError(msg, nil)
		glog.Errorf("ERROR: %s", msg.Error())
		return
	}

	// to allow to ignore seeds from a particular namespace
	if slices.Contains(c.Options.IgnoreNamespaces, seed.ObjectMeta.Namespace) {
		glog.Infof("Ignoring seeds from %s Namespace.", seed.ObjectMeta.Namespace)
		return
	}

	// to only apply seeds from a particular namespace and ignore the rest
	if len(c.Options.OnlyNamespaces) > 0 {
		if slices.Contains(c.Options.OnlyNamespaces, seed.ObjectMeta.Namespace) {
			glog.Infof("Ignoring seeds from %s Namespace. Only seeds from %v Namespaces will be applied.", seed.ObjectMeta.Namespace, c.Options.OnlyNamespaces)
			return
		}
	}

	yaml_seed, _ := yaml.Marshal(result.Spec)

	glog.V(1).Infof("Seeding %s/%s ..", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name)

	// spawn a python keystone-seeder as long as there is no functional golang keystone client
	_, err = exec.LookPath(seeder_name)
	if err != nil {
		glog.Errorf("ERROR: python %s not found.", seeder_name)
		return
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
		glog.Errorf("ERROR: could not spawn %s: %v", seeder_name, err)
	}

	stdin.Write(yaml_seed)
	stdin.Close()
	if err := cmd.Wait(); err != nil {
		msg := fmt.Errorf("failed to seed '%s/%s' - version %s: %s", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, seed.ObjectMeta.ResourceVersion, err.Error())
		raven.CaptureError(msg, nil)
		glog.Errorf("ERROR: %s", msg.Error())
		return
	}
	glog.Infof("Seeding of %s/%s - version %s done.", seed.ObjectMeta.Namespace, seed.ObjectMeta.Name, seed.ObjectMeta.ResourceVersion)
}

func (c *SeederController) resolveSeedDependencies(result *seederv1.OpenstackSeed, seed *seederv1.OpenstackSeed) (err error) {
	if result.VisitedDependencies == nil {
		result.VisitedDependencies = make(map[string]bool)
	}

	var name = seed.ObjectMeta.Namespace + "/" + seed.ObjectMeta.Name

	if result.VisitedDependencies[name] {
		// visited already, skip now
		return nil
	}

	if len(seed.Spec.Dependencies) > 0 {
		for _, v := range seed.Spec.Dependencies {
			var spec *seederv1.OpenstackSeed
			// check if the dependency contains a namespace
			dependency := strings.Split(string(v), "/")
			if len(dependency) < 2 {
				// add namespace of the spec
				spec, err = c.loadSeed(seed.ObjectMeta.Namespace + "/" + v)
			} else {
				spec, err = c.loadSeed(v)
			}
			if err != nil {
				msg := fmt.Errorf("dependency '%s' of '%s/%s' not found", v, seed.ObjectMeta.Namespace, seed.ObjectMeta.Name)
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
	result.VisitedDependencies[name] = true
	err = result.Spec.MergeSpec(seed.Spec)
	return err
}

func (c *SeederController) loadSeed(name string) (seed *seederv1.OpenstackSeed, err error) {
	seed = nil
	obj, exists, err := c.seedInformer.GetIndexer().GetByKey(name)
	if err != nil {
		glog.Errorf("lookup of %s failed: %v", name, err)
		raven.CaptureMessage("lookup failed", map[string]string{"name": name})
		return
	}
	if !exists {
		raven.CaptureMessage("spec does not exist", map[string]string{"name": name})
		err = fmt.Errorf("spec does not exist: %v", name)
		glog.Info(err)
		return
	}

	seed = obj.(*seederv1.OpenstackSeed)
	return
}
