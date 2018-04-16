/*******************************************************************************
*
* Copyright 2018 SAP SE
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
	"strconv"
	"sync"
	"syscall"

	"github.com/sapcc/kubernetes-operators/prometheus-fusion/pkg/fusion"
	"github.com/spf13/pflag"
)

var options fusion.Options

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information")
	pflag.StringVar(&options.ConfigmapAnnotation, "cm-annotation", "prometheus.io/rule", "Only configmaps with this annotation will be considered")
	pflag.StringVar(&options.PrometheusConfigMapNamespace, "prom-cm-namespace", "", "Namespace of the Prometheus configmap")
	pflag.StringVar(&options.PrometheusConfigMapName, "prom-cm-name", "", "Name of the prometheus configmap")
	pflag.StringArrayVar(&options.PreservedConfigmapKeys, "preserve-cm-keys", []string{"prometheus.yaml", "prometheus.yml"}, "Preserved keys and values of Prometheus configmap")
	pflag.IntVar(&options.MetricPort, "metric-port", 9091, "Port on which Prometheus metrics are exposed")
	pflag.IntVar(&options.RecheckPeriod, "recheck-period", 5, "RecheckPeriod[min] defines the base period after which configmaps are checked again")
	pflag.IntVar(&options.ResyncPeriod, "resync-period", 2, "ResyncPeriod[min] defines the base period after which the cache is resynced")
}

func main() {
	// Set logging output to standard console out

	log.SetOutput(os.Stdout)

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	level := 1
	// use --v flag defined by glog
	if v := pflag.Lookup("v"); v != nil {
		level, _ = strconv.Atoi(v.Value.String())
	}
	options.LogLevel = level

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	go fusion.New(options).Run(stop, wg)
	go fusion.ExposeMetrics("0.0.0.0", options.MetricPort, stop, wg)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	log.Println("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
