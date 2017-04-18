package main

import (
	"flag"
	"fmt"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"

	"github.com/golang/glog"
	"github.com/sapcc/kubernetes-operators/externalip/pkg/operator"
	"github.com/spf13/pflag"
)

var (
	options         operator.Options
	ignoreAddresses []string
	version         bool
)

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.BoolVar(&version, "version", false, "Show version and exit")
	pflag.StringVar(&options.NetworkInterface, "interface", "", "Network interface where to attach external ips")
	pflag.StringSliceVar(&ignoreAddresses, "ignore-address", []string{}, "Don't remove or add specified ip address")
}

func main() {

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	if version {
		fmt.Printf("External IP operator, version: %s\n", operator.VERSION)
		os.Exit(0)
	}

	if _, err := net.InterfaceByName(options.NetworkInterface); err != nil {
		glog.Fatal("No network interface specified or the interface doesn't exist")
	}
	for _, address := range ignoreAddresses {
		var t = address
		if !strings.Contains(address, "/") {
			t = address + "/32"
		}
		_, cidr, err := net.ParseCIDR(t)
		if err != nil {
			glog.Fatalf("Invalid IP or CIDR Range: %s", address, err)
		}
		options.IgnoreCIDR = append(options.IgnoreCIDR, *cidr)
	}

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	go operator.New(options).Run(1, stop, wg)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	glog.Infof("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
