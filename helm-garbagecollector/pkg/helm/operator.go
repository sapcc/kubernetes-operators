package helm

import (
	"log"
	"sync"
	"time"

	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/rest"
	"k8s.io/client-go/1.5/tools/clientcmd"
)

var (
	VERSION      = "0.0.0.dev"
	resyncPeriod = 5 * time.Minute
)

type Options struct {
	KubeConfig string
}

type Operator struct {
	Options

	clientset        *kubernetes.Clientset
	garbageCollector *GarbageCollector
}

func New(options Options) *Operator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		log.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	operator := &Operator{
		Options:          options,
		clientset:        clientset,
		garbageCollector: newGarbageCollector(clientset),
	}

	return operator
}

func (o *Operator) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	log.Printf("Helm Garbage Collector. Cleaning up your Helm releases! Now in version %v\n", VERSION)

	go o.garbageCollector.Run(stopCh, wg)
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
