/*
Copyright 2022 SAP SE.

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
	"fmt"
	"os"
	"time"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	_ "k8s.io/client-go/plugin/pkg/client/auth/oidc"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	discov1 "github.com/sapcc/kubernetes-operators/disco/api/v1"
	"github.com/sapcc/kubernetes-operators/disco/controllers"
	"github.com/sapcc/kubernetes-operators/disco/pkg/version"
	//+kubebuilder:scaffold:imports
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(discov1.AddToScheme(scheme))
	//+kubebuilder:scaffold:scheme
}

func main() {
	var reconciliationInterval time.Duration
	flag.DurationVar(&reconciliationInterval, "reconciliation-interval", 10*time.Minute,
		"The interval after which records are checked in Designate again regardless of whether the Kubernetes resource changed.")

	var annotation string
	flag.StringVar(&annotation, "annotation", "disco",
		"Handle ingress' and services with this annotation.")

	var metricsAddr string
	flag.StringVar(&metricsAddr, "metrics-bind-address", ":8080",
		"The address the metric endpoint binds to.")

	var probeAddr string
	flag.StringVar(&probeAddr, "health-probe-bind-address", ":8081",
		"The address the probe endpoint binds to.")

	var isPrintVersionAndExit bool
	flag.BoolVar(&isPrintVersionAndExit, "version", false,
		"Print the version and exit")

	opts := zap.Options{
		Development: true,
	}

	opts.BindFlags(flag.CommandLine)
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseFlagOptions(&opts)))

	if isPrintVersionAndExit {
		fmt.Println(version.Print("disco"))
		os.Exit(0)
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:                 scheme,
		MetricsBindAddress:     metricsAddr,
		Port:                   9443,
		HealthProbeBindAddress: probeAddr,
		LeaderElection:         true,
		LeaderElectionID:       "disco.controller",
	})
	if err != nil {
		setupLog.Error(err, "unable to start manager")
		os.Exit(1)
	}

	if err = (&controllers.RecordReconciler{
		ReconciliationInterval: reconciliationInterval,
		DefaultDNSZoneName:     os.Getenv("DEFAULT_ZONE_NAME"),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "Record")
		os.Exit(1)
	}

	if err = (&controllers.IngressShimReconciler{
		AnnotationKey: annotation,
		DefaultRecord: os.Getenv("DEFAULT_RECORD"),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "ingress-shim")
		os.Exit(1)
	}

	if err = (&controllers.ServiceShimReconciler{
		AnnotationKey: annotation,
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "service-shim")
		os.Exit(1)
	}

	//+kubebuilder:scaffold:builder

	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("starting manager")
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}
