package president

import (
	"log"
	"math/rand"
	"sync"
	"time"

	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/workqueue"
)

const CERTIFICATE_RECHECK_INTERVAL = 5 * time.Second

var (
	VERSION      = "0.0.0.dev"
	resyncPeriod = 10 * time.Minute
)

type Options struct {
	KubeConfig string

	ViceKeyFile string
	ViceCrtFile string
}

type Operator struct {
	Options

	clientset       *kubernetes.Clientset
	ingressInformer cache.SharedIndexInformer
	secretInformer  cache.SharedIndexInformer

	queue workqueue.RateLimitingInterface
}

func New(options Options) *Operator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		log.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	operator := &Operator{
		Options:   options,
		clientset: clientset,
		queue:     workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
	}

	ingressInformer := cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options meta_v1.ListOptions) (runtime.Object, error) {
				return clientset.Extensions().Ingresses(v1.NamespaceAll).List(meta_v1.ListOptions{})
			},
			WatchFunc: func(options meta_v1.ListOptions) (watch.Interface, error) {
				return clientset.Extensions().Ingresses(v1.NamespaceAll).Watch(meta_v1.ListOptions{})
			},
		},
		&v1beta1.Ingress{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	secretInformer := cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options meta_v1.ListOptions) (runtime.Object, error) {
				return clientset.Core().Secrets(v1.NamespaceAll).List(meta_v1.ListOptions{})
			},
			WatchFunc: func(options meta_v1.ListOptions) (watch.Interface, error) {
				return clientset.Core().Secrets(v1.NamespaceAll).Watch(meta_v1.ListOptions{})
			},
		},
		&v1.Secret{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.ingressAdd,
		UpdateFunc: operator.ingressUpdate,
		DeleteFunc: operator.ingressDelete,
	})

	operator.ingressInformer = ingressInformer
	operator.secretInformer = secretInformer

	return operator
}

func newClientConfig(options Options) *rest.Config {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}

	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}

	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		log.Fatalf("Couldn't get Kubernetes default config: %s", err)
	}

	return config
}

func (vp *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer vp.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)

	log.Printf("Ladies and Gentlemen, the Vice President! Renewing your Symantec certificates now in version %v\n", VERSION)

	go vp.ingressInformer.Run(stopCh)

	log.Printf("Waiting for cache to sync...")
	cache.WaitForCacheSync(stopCh, vp.ingressInformer.HasSynced)
	log.Printf("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(vp.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(CERTIFICATE_RECHECK_INTERVAL)
	go func() {
		for {
			select {
			case <-ticker.C:
				log.Printf("Next check in %v", CERTIFICATE_RECHECK_INTERVAL)
				vp.checkCertificates()
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
}

func (vp *Operator) runWorker() {
	for vp.processNextWorkItem() {
	}
}

func (vp *Operator) processNextWorkItem() bool {
	key, quit := vp.queue.Get()
	if quit {
		return false
	}
	defer vp.queue.Done(key)

	// do your work on the key.  This method will contains your "do stuff" logic
	err := vp.syncHandler(key)
	if err == nil {
		vp.queue.Forget(key)
		return true
	}

	log.Printf("%v failed with : %v", key, err)
	vp.queue.AddRateLimited(key)

	return true
}

func (vp *Operator) syncHandler(key interface{}) error {
	o, exists, err := vp.ingressInformer.GetStore().Get(key)
	if err != nil {
		return err
	}

	if !exists {
		return nil
	}

	ingress := o.(*v1beta1.Ingress)
	for _, tls := range ingress.Spec.TLS {
		log.Printf("Checking Ingress %v/%v: Hosts: %v, Secret: %v/%v", ingress.Namespace, ingress.Name, tls.Hosts, ingress.Namespace, tls.SecretName)
	}

	random := rand.Intn(640) + 1
	time.Sleep(time.Duration(random) * time.Millisecond)

	// Does Secret Exist?
	// Does the secret contain the correct keys?
	// Can the certifiate be parse?
	// Is the certificate for the correct host(s)?
	// Is the certificate still valid for time X?
	// If any error then recreate certificate

	_, err = vp.getIngressSecret(ingress)
	if err != nil {
		return err
	}

	return nil
}

func (vp *Operator) getIngressSecret(ingress *v1beta1.Ingress) (*v1.Secret, error) {
	return nil, nil
}

func (vp *Operator) ingressAdd(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	vp.queue.Add(i)
}

func (vp *Operator) ingressDelete(obj interface{}) {
}

func (vp *Operator) ingressUpdate(cur, old interface{}) {
}

func (vp *Operator) checkCertificates() {
	for _, o := range vp.ingressInformer.GetStore().List() {
		ingress := o.(*v1beta1.Ingress)
		vp.queue.Add(ingress)
	}
}
