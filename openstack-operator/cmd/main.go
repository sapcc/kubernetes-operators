package main

import (
	"flag"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/getsentry/raven-go"
	"github.com/golang/glog"
	"github.com/sapcc/kubernetes-operators/openstack-operator/pkg/seeder"
	"github.com/spf13/pflag"
	"k8s.io/kubernetes/pkg/util/logs"
	"net/http"
)

var options seeder.Options

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.BoolVar(&options.DryRun, "dry-run", false, "Only pretend to seed.")
	pflag.StringVar(&options.InterfaceType, "interface", "internal", "Openstack service interface type to use.")
	// hack around dodgy TLS rootCA handler in raven.newTransport()
	// https://github.com/getsentry/raven-go/issues/117
	t := &raven.HTTPTransport{}
	t.Client = &http.Client{
		Transport: &http.Transport{},
	}
	raven.DefaultClient.Transport = t
}

func main() {
	logs.InitLogs()
	defer logs.FlushLogs()

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	seeder.New(options).Run(stop, wg)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	glog.Info("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
