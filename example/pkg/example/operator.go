package example

import (
	"log"
	"sync"
	"time"

	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/pkg/api"
	"k8s.io/client-go/1.5/pkg/api/v1"
	"k8s.io/client-go/1.5/pkg/runtime"
	"k8s.io/client-go/1.5/pkg/watch"
	"k8s.io/client-go/1.5/tools/cache"
	"k8s.io/client-go/1.5/tools/clientcmd"
)

var (
	VERSION      = "0.0.0.dev"
	resyncPeriod = 5 * time.Minute
)

type Options struct {
	KubeConfig string
}

type Example struct {
	Options

	client      *kubernetes.Clientset
	podInformer cache.SharedIndexInformer
	debugger    *Debugger
}

func New(options Options) *Example {
	example := &Example{
		Options: options,
		client:  newClient(options.KubeConfig),
	}

	example.podInformer = cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options api.ListOptions) (runtime.Object, error) {
				return example.client.Core().Pods(v1.NamespaceAll).List(options)
			},
			WatchFunc: func(options api.ListOptions) (watch.Interface, error) {
				return example.client.Core().Pods(v1.NamespaceAll).Watch(options)
			},
		},
		&v1.Pod{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	example.debugger = newDebugger(example.podInformer)

	return example
}

func newClient(kubeConfig string) *kubernetes.Clientset {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}

	if kubeConfig != "" {
		rules.ExplicitPath = kubeConfig
	}

	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		log.Fatalf("Couldn't get Kubernetes default config: %s", err)
	}

	client, err := kubernetes.NewForConfig(config)
	if err != nil {
		log.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	log.Printf("Using Kubernetes Api at %s", config.Host)
	return client
}

func (example *Example) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	log.Printf("Welcome to Example %v\n", VERSION)

	go example.podInformer.Run(stopCh)

	cache.WaitForCacheSync(
		stopCh,
		example.podInformer.HasSynced,
	)

	go example.debugger.Run(stopCh, wg)
}
