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
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/go-kit/kit/log"
	"github.com/go-kit/kit/log/level"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/config"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/controller"
	"github.com/sapcc/kubernetes-operators/kube-fip-controller/pkg/metrics"
	"gopkg.in/alecthomas/kingpin.v2"
)

var opts config.Options

func init() {
	kingpin.Flag("kubeconfig", "Absolute path to kubeconfig").StringVar(opts.KubeConfig)
	kingpin.Flag("debug", "Enable debug logging").Default("false").BoolVar(opts.IsDebug)
	kingpin.Flag("threadiness", "The controllers threadiness").Default("1").IntVar(opts.Threadiness)
	kingpin.Flag("recheck-interval", "Interval for checking with OpenStack.").Default("5m").DurationVar(opts.RecheckInterval)
	kingpin.Flag("default-floating-network", "Name of the default Floating IP network.").Required().StringVar(opts.DefaultFloatingNetwork)
	kingpin.Flag("default-floating-subnet", "Name of the default Floating IP subnet.").Required().StringVar(opts.DefaultFloatingSubnet)
	kingpin.Flag("config", "Absolute path to configuration file.").Required().StringVar(opts.ConfigPath)
}

func main() {
	kingpin.Parse()

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	defer close(stop)

	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM)
	wg := &sync.WaitGroup{}

	logLevel := level.AllowInfo()
	if *opts.IsDebug {
		logLevel = level.AllowDebug()
	}

	logger := log.NewLogfmtLogger(os.Stdout)
	logger = level.NewFilter(logger, logLevel)
	logger = log.With(logger, "ts", log.DefaultTimestampUTC, "caller", log.Caller(3))

	c, err := controller.New(opts, logger)
	if err != nil {
		level.Error(logger).Log("msg", "fatal error starting the controller", "err", err)
		return
	}

	go c.Run(*opts.Threadiness, stop)
	go metrics.ServeMetrics(*opts.MetricHost, *opts.MetricPort, wg, stop, logger)

	<-sigs
	level.Info(logger).Log("msg", "shutting down")

	wg.Wait()
}
