/*******************************************************************************
*
* Copyright 2017 SAP SE
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You should have received a copy of the License along with this
* program. If not, you may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
*******************************************************************************/

package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/sapcc/kubernetes-operators/vice-president/pkg/president"
	"github.com/spf13/pflag"
)

var options president.Options

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.StringVar(&options.VicePresidentConfig, "vice-president-config", "/etc/vice-president/config/vice-president.conf", "Path to VICE President config file with certificate parameters.")
	pflag.StringVar(&options.ViceCrtFile, "vice-cert", "/etc/vice-president/secrets/vice.cert", "A PEM encoded certificate file.")
	pflag.StringVar(&options.ViceKeyFile, "vice-key", "/etc/vice-president/secrets/vice.key", "A PEM encoded private key file.")
	pflag.StringVar(&options.IngressAnnotation, "ingress-annotation", "vice-president", "Only an ingress with this annotation will be considered. Must be vice-president:true")
	pflag.StringVar(&options.MetricListenAddress, "metric-listen-address", "9091", "Port on which Prometheus metrics are exposed.")
}

func main() {
	// Set logging output to standard console out

	log.SetOutput(os.Stdout)

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	go president.New(options).Run(10, stop, wg)
	go president.ExposeMetrics(options.MetricListenAddress)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	log.Printf("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
