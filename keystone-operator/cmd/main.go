package main

import (
	"flag"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/golang/glog"
	"github.com/spf13/pflag"
	"github.com/sapcc/kubernetes-operators/keystone-operator/pkg/seeder"
	"k8s.io/kubernetes/pkg/util/logs"
)

var options seeder.Options

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
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
