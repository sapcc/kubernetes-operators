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
	KubeConfig    string
	DryRun        bool
	InterfaceType string
}

type OpenstackOperator struct {
	Options

	clientset    *kubernetes.Clientset
	seederClient *rest.RESTClient

	seedManager *OpenstackSeedManager
}

func New(options Options) *OpenstackOperator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	seederClient, err := NewOpenstackSeedClientForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create OpenstackSeed client: %s", err)
	}

	seeder := &OpenstackOperator{
		Options:      options,
		clientset:    clientset,
		seederClient: seederClient,
		seedManager:  newOpenstackSeedManager(seederClient, clientset, &options),
	}

	return seeder
}

func (seeder *OpenstackOperator) Run(stopCh <-chan struct{}, wg *sync.WaitGroup) {
	glog.Infof("Welcome to OpenstackOperator %v\n", VERSION)

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
