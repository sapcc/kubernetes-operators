package operator

import (
	"sync"
	"time"

	"github.com/golang/glog"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/fields"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"

	tprv1 "github.com/sapcc/kubernetes-operators/sentry/pkg/tpr/v1"
)

const (
	TPR_RECHECK_INTERVAL = 5 * time.Minute
	CACHE_RESYNC_PERIOD  = 10 * time.Minute
)

type Operator struct {
	Options

	clientset   *kubernetes.Clientset
	tprClient   *rest.RESTClient
	tprScheme   *runtime.Scheme
	tprInformer cache.SharedIndexInformer
	queue       workqueue.RateLimitingInterface
}

func New(options Options) *Operator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	if err := CreateTPR(clientset); err != nil && !apierrors.IsAlreadyExists(err) {
		glog.Fatalf("Failed to create TPR resource: %s", err)
	}

	tprClient, scheme, err := NewClient(config)
	if err != nil {
		glog.Fatalf("Couldn't create TPR client: %s", err)
	}

	if err := WaitForSentyProjectResource(tprClient); err != nil {
		glog.Fatalf("Timout waiting for TPR to be ready")
	}

	operator := &Operator{
		Options:   options,
		clientset: clientset,
		tprClient: tprClient,
		tprScheme: scheme,
		queue:     workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
	}

	tprInformer := cache.NewSharedIndexInformer(
		cache.NewListWatchFromClient(tprClient, tprv1.SentryProjectResourcePlural, v1.NamespaceAll, fields.Everything()),
		&tprv1.SentryProject{},
		CACHE_RESYNC_PERIOD,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)
	tprInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.sentryProjectAdd,
		UpdateFunc: operator.sentryProjectUpdate,
		DeleteFunc: operator.sentryProjectDelete,
	})
	operator.tprInformer = tprInformer

	return operator
}

func (op *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer op.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)
	glog.Infof("Sentry operator started!  %v\n", VERSION)

	go op.tprInformer.Run(stopCh)

	glog.Info("Waiting for cache to sync...")
	cache.WaitForCacheSync(stopCh, op.tprInformer.HasSynced)
	glog.Info("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(op.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(TPR_RECHECK_INTERVAL)
	go func() {
		for {
			select {
			case <-ticker.C:
				glog.V(2).Infof("Next reconciliation check in %v", TPR_RECHECK_INTERVAL)
				op.queue.Add(true)
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
}

func (op *Operator) runWorker() {
	for op.processNextWorkItem() {
	}
}

func (op *Operator) processNextWorkItem() bool {
	key, quit := op.queue.Get()
	if quit {
		return false
	}
	defer op.queue.Done(key)

	// do your work on the key.  This method will contains your "do stuff" logic
	err := op.handler(key)
	if err == nil {
		op.queue.Forget(key)
		return true
	}

	glog.Warningf("Error running syncHandler: %v", err)
	op.queue.AddRateLimited(key)

	return true
}

func (op *Operator) handler(key interface{}) error {
	return nil
}

func (op *Operator) sentryProjectAdd(obj interface{}) {
	proj := obj.(*tprv1.SentryProject)
	glog.Info("Added sentry project: ", proj.GetName())
	//op.queue.Add(true)
}

func (op *Operator) sentryProjectDelete(obj interface{}) {
	proj := obj.(*tprv1.SentryProject)
	glog.Info("Deleted sentry project ", proj.GetName())
	//op.queue.Add(true)
}

func (op *Operator) sentryProjectUpdate(cur, old interface{}) {
	curProj := cur.(*tprv1.SentryProject)
	//oldProj := old.(*tprv1.SentryProject)

	glog.Info("sentry project updated ", curProj.GetName())
	//op.queue.Add(true)
}
