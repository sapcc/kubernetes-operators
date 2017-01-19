package seeder

import (
	"flag"
	"fmt"
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

type KeystoneSeedManager struct {
	seederClient *rest.RESTClient
	clientset    *kubernetes.Clientset

	seedInformer cache.SharedIndexInformer
}

func newKeystoneSeedManager(seederClient *rest.RESTClient, clientset *kubernetes.Clientset) *KeystoneSeedManager {
	seedManager := &KeystoneSeedManager{
		seederClient: seederClient,
		clientset:    clientset,
	}

	seedInformer := cache.NewSharedIndexInformer(
		cache.NewListWatchFromClient(seederClient, "keystoneseeds", api.NamespaceAll, fields.Everything()),
		&KeystoneSeed{},
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

func (mgr *KeystoneSeedManager) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer wg.Done()
	wg.Add(1)

	if err := EnsureKeystoneSeedThirdPartyResource(mgr.clientset); err != nil {
		glog.Fatalf("ERROR: couldn't create KeystoneSeed ThirdPartyResource: %s", err)
	}

	go mgr.seedInformer.Run(stopCh)

	<-stopCh
}

func (mgr *KeystoneSeedManager) seedAdd(obj interface{}) {
	seed := obj.(*KeystoneSeed)
	if seed.Metadata.Name != "" {
		glog.Infof("Added %s/%s - version: %s", seed.Metadata.Namespace, seed.Metadata.Name, seed.Metadata.ResourceVersion)
		mgr.seedApply(seed)
	}
}

func (mgr *KeystoneSeedManager) seedDelete(obj interface{}) {
	seed := obj.(*KeystoneSeed)
	glog.Infof("Deleted %s/%s - version: %s", seed.Metadata.Namespace, seed.Metadata.Name, seed.Metadata.ResourceVersion)
}

func (mgr *KeystoneSeedManager) seedUpdate(old, new interface{}) {
	oldSeed := old.(*KeystoneSeed)
	newSeed := new.(*KeystoneSeed)

	if newSeed.Metadata.Name != "" {
		if newSeed.Metadata.ResourceVersion == oldSeed.Metadata.ResourceVersion {
			return
		}
		glog.Infof("Updated %s/%s - version: %s", newSeed.Metadata.Namespace, newSeed.Metadata.Name, newSeed.Metadata.ResourceVersion)
		mgr.seedApply(newSeed)
	}
}

func (mgr *KeystoneSeedManager) seedApply(seed *KeystoneSeed) {
	result := new(KeystoneSeed)
	result.Metadata = seed.Metadata
	err := mgr.resolveSeedDependencies(result, seed)

	if err != nil {
		glog.Errorf("ERROR: failed to process '%s/%s': %v", seed.Metadata.Namespace, seed.Metadata.Name, err)
		return
	}

	yaml_seed, _ := yaml.Marshal(result.Spec)

	glog.V(1).Infof("Seeding %s:\n%s", seed.Metadata.Name, string(yaml_seed))

	// spawn a python keystone-seeder as long as there is no functional golang keystone client

	path, err := exec.LookPath("keystone-seeder")
	if err != nil {
		glog.Error("ERROR: python keystone-seeder not found.")
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

	cmd := exec.Command("keystone-seeder", "--interface", "internal", "-l", level)

	// inherit the os-environment
	env := os.Environ()
	cmd.Env = env

	glog.V(2).Infof("Spawning %s, env: %s", path, cmd.Env)

	stdin, err := cmd.StdinPipe()
	if err != nil {
		fmt.Println(err)
	}

	defer stdin.Close()

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err = cmd.Start(); err != nil {
		glog.Error("ERROR: could not spawn keystone-seeder: ", err)
	}

	stdin.Write(yaml_seed)
	stdin.Close()
	if err := cmd.Wait(); err != nil {
		glog.Error("ERROR: keystone-seeder failed with", err)
		return
	}
	glog.Infof("Seeding %s done.", seed.Metadata.Name)
}

func (mgr *KeystoneSeedManager) resolveSeedDependencies(result *KeystoneSeed, seed *KeystoneSeed) (err error) {
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
			var spec *KeystoneSeed
			// check if the dependency contains a namespace
			dependency := strings.Split(string(v), "/")
			if len(dependency) < 2 {
				// add namespace of the spec
				spec, err = mgr.loadSeed(seed.Metadata.Namespace + "/" + v)
			} else {
				spec, err = mgr.loadSeed(v)
			}
			if err != nil {
				glog.Errorf("ERROR: dependency '%s' of '%s' not found.", v, name)
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

func (mgr *KeystoneSeedManager) loadSeed(name string) (seed *KeystoneSeed, err error) {
	seed = nil
	obj, exists, err := mgr.seedInformer.GetIndexer().GetByKey(name)
	if err != nil {
		glog.Errorf("lookup of %s failed: %v", name, err)
		return
	}
	if !exists {
		err = fmt.Errorf("spec does not exist: %v", name)
		return
	}

	seed = obj.(*KeystoneSeed)
	return
}
