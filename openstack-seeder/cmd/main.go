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

// Note: the example only works with the code within the same release/branch.
package main

import (
	"context"
	"flag"
	"net/http"

	// Uncomment the following line to load the gcp plugin (only required to authenticate against GKE clusters).
	// _ "k8s.io/client-go/plugin/pkg/client/auth/gcp"

	"github.com/getsentry/raven-go"
	"github.com/golang/glog"
	seedercontroller "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/controller"
	"github.com/spf13/pflag"
	"k8s.io/kubernetes/pkg/util/logs"
)

var options seedercontroller.Options

func main() {
	logs.InitLogs()
	defer logs.FlushLogs()

	// hack around dodgy TLS rootCA handler in raven.newTransport()
	// https://github.com/getsentry/raven-go/issues/117
	t := &raven.HTTPTransport{}
	t.Client = &http.Client{
		Transport: &http.Transport{},
	}
	raven.DefaultClient.Transport = t

	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.BoolVar(&options.DryRun, "dry-run", false, "Only pretend to seed.")
	pflag.StringVar(&options.InterfaceType, "interface", "internal", "Openstack service interface type to use.")
	pflag.StringArrayVar(&options.IgnoreNamespaces, "ignorenamespace", nil, "Ignore seeds from a certain k8s Namespace (can be given multiple times to ignore multiple namespaces).")
	pflag.StringArrayVar(&options.OnlyNamespaces, "onlynamespace", nil, "Only apply seeds from a certain k8s Namespace (can be given multiple times to watch multiple namespaces).")
	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	ctx, cancelFunc := context.WithCancel(context.Background())
	defer cancelFunc()

	seedercontroller.New(options).Run(ctx)

	glog.Info("Shutting down...")
}
