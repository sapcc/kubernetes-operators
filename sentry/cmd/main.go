package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/golang/glog"
	"github.com/sapcc/kubernetes-operators/sentry/pkg/operator"
	"github.com/spf13/pflag"
)

var options operator.Options
var showVersion bool

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.StringVar(&options.SentryEndpoint, "sentry-endpoint", "https://sentry.io/api/0", "Endpoint for the sentry api")
	pflag.StringVar(&options.SentryToken, "sentry-token", "", "Auth token for the sentry api")
	pflag.StringVar(&options.SentryOrganization, "sentry-organization", "", "Slug for the sentry organization where projects are created")
	pflag.BoolVar(&showVersion, "version", false, "Show version and exit")
}

func main() {

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()
	//https://github.com/kubernetes/kubernetes/issues/17162
	flag.CommandLine.Parse([]string{})

	if showVersion {
		fmt.Printf("sentry operator, version: %s\n", operator.VERSION)
		os.Exit(0)
	}

	if options.SentryEndpoint == "" {
		options.SentryEndpoint = os.Getenv("SENTRY_ENDPOINT")
	}

	if options.SentryToken == "" {
		if os.Getenv("SENTRY_TOKEN") == "" {
			glog.Fatal("sentry-token not given")
		}
		options.SentryToken = os.Getenv("SENTRY_TOKEN")
	}

	if options.SentryOrganization == "" {
		if os.Getenv("SENTRY_ORGANIZATION") == "" {
			glog.Fatal("sentry-organization not given")
		}
		options.SentryOrganization = os.Getenv("SENTRY_ORGANIZATION")
	}

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	go operator.New(options).Run(1, stop, wg)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	glog.Info("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
