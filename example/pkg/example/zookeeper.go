package example

import (
	"log"
	"sync"

	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/pkg/api"
	"k8s.io/client-go/1.5/pkg/fields"
	"k8s.io/client-go/1.5/rest"
	"k8s.io/client-go/1.5/tools/cache"
)

type ZooKeeper struct {
	critterClient *rest.RESTClient
	clientset     *kubernetes.Clientset

	critterInformer cache.SharedIndexInformer
}

func newZookeeper(critterClient *rest.RESTClient, clientset *kubernetes.Clientset) *ZooKeeper {
	zooKeeper := &ZooKeeper{
		critterClient: critterClient,
		clientset:     clientset,
	}

	critterInformer := cache.NewSharedIndexInformer(
		cache.NewListWatchFromClient(critterClient, "critters", api.NamespaceAll, fields.Everything()),
		&Critter{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	critterInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    zooKeeper.critterAdd,
		UpdateFunc: zooKeeper.critterUpdate,
		DeleteFunc: zooKeeper.critterDelete,
	})

	zooKeeper.critterInformer = critterInformer

	return zooKeeper
}

func (z *ZooKeeper) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer wg.Done()
	wg.Add(1)

	if err := EnsureCritterThirdPartyResource(z.clientset); err != nil {
		log.Fatalf("Couldn't create ThirdPartyResource: %s", err)
	}

	go z.critterInformer.Run(stopCh)

	<-stopCh
}

func (z *ZooKeeper) critterAdd(obj interface{}) {
	critter := obj.(*Critter)
	log.Printf("Critter ADDED: %s's new %s is %s", critter.Spec.Owner, critter.Metadata.Name, critter.Spec.Color)
}

func (z *ZooKeeper) critterDelete(obj interface{}) {
	critter := obj.(*Critter)
	log.Printf("Critter DELETED: %s's %s %s just died... :(", critter.Spec.Owner, critter.Spec.Color, critter.Metadata.Name)
}

func (z *ZooKeeper) critterUpdate(cur, old interface{}) {
	oldCritter := old.(*Critter)
	curCritter := cur.(*Critter)

	if curCritter.Spec.Owner != oldCritter.Spec.Owner {
		log.Printf("Critter UPDATED: %s gave a %s %s to %s", oldCritter.Spec.Owner, oldCritter.Spec.Color, oldCritter.Metadata.Name, curCritter.Spec.Owner)
	}

	if curCritter.Spec.Color != oldCritter.Spec.Color {
		log.Printf("Critter UPDATED: Hm. %s's %s just changed color from %s to %s", curCritter.Spec.Owner, curCritter.Metadata.Name, oldCritter.Spec.Color, curCritter.Spec.Color)
	}
}
