// Copyright 2017 SAP SE
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package seeder

import (
	"flag"
	"fmt"
	"github.com/getsentry/raven-go"
	"github.com/golang/glog"
	"gopkg.in/yaml.v2"
	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/pkg/api"
	"k8s.io/client-go/1.5/pkg/fields"
	"k8s.io/client-go/1.5/rest"
	"k8s.io/client-go/1.5/tools/cache"
	"os"
	"os/exec"
	"strings"
	"sync"
)

type OpenstackSeedManager struct {
	options      *Options
	seederClient *rest.RESTClient
	clientset    *kubernetes.Clientset

	seedInformer cache.SharedIndexInformer
}

func newOpenstackSeedManager(seederClient *rest.RESTClient, clientset *kubernetes.Clientset, options *Options) *OpenstackSeedManager {
	seedManager := &OpenstackSeedManager{
		options:      options,
		seederClient: seederClient,
		clientset:    clientset,
	}

	seedInformer := cache.NewSharedIndexInformer(
		cache.NewListWatchFromClient(seederClient, "openstackseeds", api.NamespaceAll, fields.Everything()),
		&OpenstackSeed{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	seedInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    seedManager.seedAdd,
		UpdateFunc: seedManager.seedUpdate,
		DeleteFunc: seedManager.seedDelete,
	})

	seedManager.seedInformer = seedInformer

	return seedManager
}

func (mgr *OpenstackSeedManager) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer wg.Done()
	wg.Add(1)

	if err := EnsureOpenstackSeedThirdPartyResource(mgr.clientset); err != nil {
		msg := fmt.Errorf("ERROR: couldn't create OpenstackSeed ThirdPartyResource: %s", err.Error())
		raven.CaptureErrorAndWait(msg, nil)
		glog.Fatal(msg)
	}

	go mgr.seedInformer.Run(stopCh)

	<-stopCh
}

func (mgr *OpenstackSeedManager) seedAdd(obj interface{}) {
	seed := obj.(*OpenstackSeed)
	if seed.Metadata.Name != "" {
		glog.Infof("Added %s/%s - version: %s", seed.Metadata.Namespace, seed.Metadata.Name, seed.Metadata.ResourceVersion)
		mgr.seedApply(seed)
	}
}

func (mgr *OpenstackSeedManager) seedDelete(obj interface{}) {
	seed := obj.(*OpenstackSeed)
	glog.Infof("Deleted %s/%s - version: %s", seed.Metadata.Namespace, seed.Metadata.Name, seed.Metadata.ResourceVersion)
}

func (mgr *OpenstackSeedManager) seedUpdate(old, new interface{}) {
	oldSeed := old.(*OpenstackSeed)
	newSeed := new.(*OpenstackSeed)

	if newSeed.Metadata.Name != "" {
		if newSeed.Metadata.ResourceVersion == oldSeed.Metadata.ResourceVersion {
			return
		}
		glog.Infof("Updated %s/%s - version: %s", newSeed.Metadata.Namespace, newSeed.Metadata.Name, newSeed.Metadata.ResourceVersion)
		mgr.seedApply(newSeed)
	}
}

func (mgr *OpenstackSeedManager) seedApply(seed *OpenstackSeed) {
	const seeder_name string = "openstack-seeder"
	result := new(OpenstackSeed)
	result.Metadata = seed.Metadata
	err := mgr.resolveSeedDependencies(result, seed)

	if err != nil {
		msg := fmt.Errorf("failed to process openstackseed '%s/%s': %s", seed.Metadata.Namespace, seed.Metadata.Name, err.Error())
		raven.CaptureError(msg, nil)
		glog.Errorf("ERROR: %s", msg.Error())
		return
	}

	yaml_seed, _ := yaml.Marshal(result.Spec)

	glog.V(1).Infof("Seeding %s/%s ..", seed.Metadata.Namespace, seed.Metadata.Name)

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

	cmd := exec.Command(seeder_name, "--interface", mgr.options.InterfaceType, "-l", level)
	if mgr.options.DryRun {
		cmd = exec.Command(seeder_name, "--interface", mgr.options.InterfaceType, "-l", level, "--dry-run")
	}

	// inherit the os-environment
	env := os.Environ()
	cmd.Env = env

	glog.V(2).Infof("Spawning %s, args: %s, env: %s", cmd.Path, cmd.Args, cmd.Env)

	stdin, err := cmd.StdinPipe()
	if err != nil {
		fmt.Println(err)
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
		msg := fmt.Errorf("failed to seed '%s/%s': %s", seed.Metadata.Namespace, seed.Metadata.Name, err.Error())
		raven.CaptureError(msg, nil)
		glog.Errorf("ERROR: %s", msg.Error())
		return
	}
	glog.Infof("Seeding %s/%s done.", seed.Metadata.Namespace, seed.Metadata.Name)
}

func (mgr *OpenstackSeedManager) resolveSeedDependencies(result *OpenstackSeed, seed *OpenstackSeed) (err error) {
	if result.VisitedDependencies == nil {
		result.VisitedDependencies = make(map[string]bool)
	}

	var name = seed.Metadata.Namespace + "/" + seed.Metadata.Name

	if result.VisitedDependencies[name] {
		// visited already, skip now
		return nil
	}

	if len(seed.Spec.Dependencies) > 0 {
		for _, v := range seed.Spec.Dependencies {
			var spec *OpenstackSeed
			// check if the dependency contains a namespace
			dependency := strings.Split(string(v), "/")
			if len(dependency) < 2 {
				// add namespace of the spec
				spec, err = mgr.loadSeed(seed.Metadata.Namespace + "/" + v)
			} else {
				spec, err = mgr.loadSeed(v)
			}
			if err != nil {
				msg := fmt.Errorf("dependency '%s' of '%s/%s' not found", v, seed.Metadata.Namespace, seed.Metadata.Name)
				raven.CaptureError(msg, nil)
				glog.Errorf("ERROR: %s", msg.Error())
				return err
			}
			glog.Infof("Processing dependency '%s' of '%s'.", v, name)
			err = mgr.resolveSeedDependencies(result, spec)
			if err != nil {
				return err
			}
		}
	}
	result.VisitedDependencies[name] = true
	err = result.Spec.MergeSpec(seed.Spec)
	return err
}

func (mgr *OpenstackSeedManager) loadSeed(name string) (seed *OpenstackSeed, err error) {
	seed = nil
	obj, exists, err := mgr.seedInformer.GetIndexer().GetByKey(name)
	if err != nil {
		raven.CaptureMessage("lookup failed", map[string]string{"name": name})
		glog.Errorf("lookup of %s failed: %v", name, err)
		return
	}
	if !exists {
		raven.CaptureMessage("spec does not exist", map[string]string{"name": name})
		err = fmt.Errorf("spec does not exist: %v", name)
		return
	}

	seed = obj.(*OpenstackSeed)
	return
}
