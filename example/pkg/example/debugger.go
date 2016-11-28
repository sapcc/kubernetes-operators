package example

import (
	"log"
	"sync"

	"k8s.io/client-go/1.5/pkg/api/v1"
	"k8s.io/client-go/1.5/tools/cache"
)

type Debugger struct {
	pods cache.Store
}

func newDebugger(pods cache.SharedInformer) *Debugger {
	debugger := &Debugger{}

	pods.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    debugger.podAdd,
		UpdateFunc: debugger.podUpdate,
		DeleteFunc: debugger.podDelete,
	})

	return debugger
}

func (c *Debugger) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer wg.Done()
	wg.Add(1)

	<-stopCh
}

func (p *Debugger) podAdd(obj interface{}) {
	pod := obj.(*v1.Pod)
	log.Printf("ADD %s/%s", pod.Namespace, pod.Name)
}

func (p *Debugger) podDelete(obj interface{}) {
	pod := obj.(*v1.Pod)
	log.Printf("DELETE %s/%s", pod.Namespace, pod.Name)
}

func (p *Debugger) podUpdate(cur, old interface{}) {
	pod := cur.(*v1.Pod)
	log.Printf("UPDATE %s/%s", pod.Namespace, pod.Name)
}
