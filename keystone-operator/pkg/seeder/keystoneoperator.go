package seeder

import (
	"github.com/golang/glog"
	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/rest"
	"k8s.io/client-go/1.5/tools/clientcmd"
	"sync"
	"time"
)

var (
	VERSION      = "0.0.1.dev"
	resyncPeriod = 5 * time.Minute
)

type Options struct {
	KubeConfig string
}

type KeystoneOperator struct {
	Options

	clientset    *kubernetes.Clientset
	seederClient *rest.RESTClient

	seedManager *KeystoneSeedManager
}

func New(options Options) *KeystoneOperator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	seederClient, err := NewKeystoneSeedClientForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create KeystoneSeed client: %s", err)
	}

	seeder := &KeystoneOperator{
		Options:      options,
		clientset:    clientset,
		seederClient: seederClient,
		seedManager:  newKeystoneSeedManager(seederClient, clientset),
	}

	return seeder
}

func (seeder *KeystoneOperator) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	glog.Infof("Welcome to KeystoneOperator %v\n", VERSION)

	go seeder.seedManager.Run(stopCh, wg)
}

func newClientConfig(options Options) *rest.Config {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}

	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}

	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		glog.Fatalf("Couldn't get Kubernetes default config: %s", err)
	}

	return config
}
