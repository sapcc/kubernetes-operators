/*******************************************************************************
*
* Copyright 2019 SAP SE
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
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/sapcc/kubernetes-operators/disco/pkg/disco"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
	"github.com/sapcc/kubernetes-operators/disco/pkg/metrics"
	"github.com/spf13/pflag"
)

var (
	options disco.Options
)

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information")
	pflag.StringVar(&options.ConfigPath, "config", "/etc/disco/disco.conf", "Path to operator config file")
	pflag.StringVar(&options.IngressAnnotation, "ingress-annotation", disco.DefaultIngressAnnotation, "Handle ingress with this annotation")
	pflag.IntVar(&options.Threadiness, "threadiness", disco.DefaultThreadiness, "The operator threadiness")
	pflag.IntVar(&options.MetricPort, "metric-port", disco.DefaultMetricPort, "Metrics are exposed on this port")
	pflag.IntVar(&options.RecheckPeriod, "recheck-period", disco.DefaultRecheckPeriod, "RecheckPeriod[min] defines the base period after which configmaps are checked again")
	pflag.IntVar(&options.ResyncPeriod, "resync-period", disco.DefaultResyncPeriod, "ResyncPeriod[min] defines the base period after which the cache is resynced")
	pflag.IntVar(&options.RecordsetTTL, "recordset-ttl", disco.DefaultRecordsetTTL, "The Recordset TTL in seconds")
	pflag.StringVar(&options.Record, "record", "", "Default record data used for the CNAME")
	pflag.StringVar(&options.ZoneName, "zone-name", "", "Name of the openstack zone in which the recordset will be created")
	pflag.BoolVar(&options.IsDebug, "debug", false, "Enable debug logging")
}

func main() {
	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	logger := log.NewLogger(options.IsDebug)

	go disco.New(options, logger).Run(options.Threadiness, stop, wg)
	go metrics.ExposeMetrics("0.0.0.0", options.MetricPort, stop, wg, logger)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	logger.LogInfo("Stopping the music..")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
