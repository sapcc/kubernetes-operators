/*
Copyright 2017 SAP SE

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package main

import (
	"flag"
	// Uncomment the following line to load the gcp plugin (only required to authenticate against GKE clusters).
	// _ "k8s.io/client-go/plugin/pkg/client/auth/gcp"

	"net/http"
	"time"

	"github.com/getsentry/raven-go"
	"github.com/golang/glog"
	clientset "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/client/clientset/versioned"
	informers "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/client/informers/externalversions"
	seedercontroller "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/controller"
	"github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/signals"
	"github.com/spf13/pflag"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	kubeinformers "k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

var options seedercontroller.Options

func main() {
	pflag.Parse()

	// hack around dodgy TLS rootCA handler in raven.newTransport()
	// https://github.com/getsentry/raven-go/issues/117
	t := &raven.HTTPTransport{}
	t.Client = &http.Client{
		Transport: &http.Transport{},
	}
	raven.DefaultClient.Transport = t

	// set up signals so we handle the first shutdown signal gracefully
	stopCh := signals.SetupSignalHandler()

	cfg, err := clientcmd.BuildConfigFromFlags(options.MasterURL, options.KubeConfig)
	if err != nil {
		glog.Fatalf("Error building kubeconfig: %s", err.Error())
	}

	kubeClient, err := kubernetes.NewForConfig(cfg)
	if err != nil {
		glog.Fatalf("Error building kubernetes clientset: %s", err.Error())
	}

	apiextensionsClient, err := apiextensionsclient.NewForConfig(cfg)
	if err != nil {
		glog.Fatalf("Error building api-extension clientset: %v", err)
	}

	seederClient, err := clientset.NewForConfig(cfg)
	if err != nil {
		glog.Fatalf("Error building seeder clientset: %s", err.Error())
	}

	kubeInformerFactory := kubeinformers.NewSharedInformerFactory(kubeClient, options.ResyncPeriod)
	seederInformerFactory := informers.NewSharedInformerFactory(seederClient, options.ResyncPeriod)

	controller := seedercontroller.NewController(options, kubeClient, apiextensionsClient, seederClient,
		seederInformerFactory.Openstack().V1().OpenstackSeeds())

	go kubeInformerFactory.Start(stopCh)
	go seederInformerFactory.Start(stopCh)

	if err = controller.Run(options.Threadiness, stopCh); err != nil {
		glog.Fatalf("Error running controller: %s", err.Error())
	}

	glog.Info("Shutting down...")
}

func init() {
	pflag.StringVar(&options.MasterURL, "master-url", "", "URL of the kubernetes master.")
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.BoolVar(&options.DryRun, "dry-run", false, "Only pretend to seed.")
	pflag.StringVar(&options.InterfaceType, "interface", "internal", "Openstack service interface type to use.")
	pflag.DurationVar(&options.ResyncPeriod, "resync", time.Hour*24, "Resync period")
	pflag.StringSliceVar(&options.IgnoreNamespaces, "ignorenamespace", nil, "Ignore seeds from a certain k8s Namespace (can be given multiple times to ignore multiple namespaces).")
	pflag.StringSliceVar(&options.OnlyNamespaces, "onlynamespace", nil, "Only apply seeds from a certain k8s Namespace (can be given multiple times to watch multiple namespaces).")
	pflag.IntVar(&options.Threadiness, "threadiness", 1, "Operator threadiness.")
	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
}
