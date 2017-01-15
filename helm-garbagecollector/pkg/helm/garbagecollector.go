package helm

import (
	"log"
	"sort"
	"strconv"
	"sync"
	"time"

	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/pkg/api"
	"k8s.io/client-go/1.5/pkg/api/v1"
	"k8s.io/client-go/1.5/pkg/labels"
	"k8s.io/client-go/1.5/pkg/runtime"
	"k8s.io/client-go/1.5/pkg/watch"
	"k8s.io/client-go/1.5/tools/cache"
)

const REVISION_HISTORY_LIMIT = 5
const GARBAGE_COLLECTION_INTERVAL = 5 * time.Minute

type GarbageCollector struct {
	clientset *kubernetes.Clientset
	informer  cache.SharedIndexInformer
}

type ByVersion []*v1.ConfigMap

func (s ByVersion) Len() int {
	return len(s)
}
func (s ByVersion) Swap(i, j int) {
	s[i], s[j] = s[j], s[i]
}
func (s ByVersion) Less(i, j int) bool {
	a, _ := strconv.Atoi(s[i].Labels["VERSION"])
	b, _ := strconv.Atoi(s[j].Labels["VERSION"])
	return a < b
}

func newGarbageCollector(clientset *kubernetes.Clientset) *GarbageCollector {
	garbageCollector := &GarbageCollector{
		clientset: clientset,
	}

	releaseInformer := cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options api.ListOptions) (runtime.Object, error) {
				options.LabelSelector = labels.SelectorFromSet(map[string]string{"OWNER": "TILLER"})
				return clientset.Core().ConfigMaps("kube-system").List(options)
			},
			WatchFunc: func(options api.ListOptions) (watch.Interface, error) {
				return clientset.Core().ConfigMaps("kube-system").Watch(options)
			},
		},
		&v1.ConfigMap{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	releaseInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    garbageCollector.releaseAdd,
		UpdateFunc: garbageCollector.releaseUpdate,
		DeleteFunc: garbageCollector.releaseDelete,
	})

	garbageCollector.informer = releaseInformer

	return garbageCollector
}

func (gc *GarbageCollector) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer wg.Done()
	wg.Add(1)

	go gc.informer.Run(stopCh)
	log.Printf("Waiting for cache to sync. For a lot of Helm releases this might take minutes...")
	cache.WaitForCacheSync(stopCh, gc.informer.HasSynced)

	ticker := time.NewTicker(GARBAGE_COLLECTION_INTERVAL)
	go func() {
		for {
			select {
			case <-ticker.C:
				gc.collectGarbage()
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()
	<-stopCh
}

func (gc *GarbageCollector) collectGarbage() {
	log.Printf("Collecting Garbage:")

	releases := make(map[string][]*v1.ConfigMap)

	for _, o := range gc.informer.GetStore().List() {
		cm := o.(*v1.ConfigMap)

		if cm.Labels["STATUS"] != "SUPERSEDED" {
			continue
		}

		name := cm.Labels["NAME"]

		if releases[name] == nil {
			releases[name] = make([]*v1.ConfigMap, 0)
		}

		releases[name] = append(releases[name], cm)
	}

	for _, v := range releases {
		sort.Sort(ByVersion(v))
	}

	for name, superseeded := range releases {
		deleteCount := len(superseeded) - REVISION_HISTORY_LIMIT

		if deleteCount <= 0 {
			continue
		}

		log.Printf("Found %v superseeded releases for %v. Will delete %v!", len(superseeded), name, deleteCount)

		for _, release := range superseeded[:deleteCount] {
			log.Printf("Deleting %s", release.GetName())
			gc.deleteRelease(release.GetName())
		}
	}
}

func (gc *GarbageCollector) deleteRelease(name string) {
	gc.clientset.ConfigMaps("kube-system").Delete(name, &api.DeleteOptions{})
}

func (gc *GarbageCollector) releaseAdd(obj interface{}) {
	release := obj.(*v1.ConfigMap)
	log.Printf("Release ADDED: %s with Status %s in version %s", release.Labels["NAME"], release.Labels["STATUS"], release.Labels["VERSION"])
}

func (gc *GarbageCollector) releaseUpdate(cur, old interface{}) {
	oldRelease := old.(*v1.ConfigMap)
	curRelease := cur.(*v1.ConfigMap)

	log.Printf("Release Updated: %s was %s/%s and is now %s/%s", curRelease.Labels["NAME"], oldRelease.Labels["STATUS"], oldRelease.Labels["VERSION"], curRelease.Labels["STATUS"], curRelease.Labels["VERSION"])
}

func (gc *GarbageCollector) releaseDelete(obj interface{}) {
	release := obj.(*v1.ConfigMap)
	log.Printf("Release DELETED: %s with Status %s in version %s", release.Labels["NAME"], release.Labels["STATUS"], release.Labels["VERSION"])
}
