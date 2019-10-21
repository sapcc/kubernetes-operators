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
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/config"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/president"
	"github.com/spf13/pflag"
)

var options config.Options

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.StringVar(&options.VicePresidentConfig, "vice-president-config", "/etc/vice-president/config/vice-president.conf", "Path to VICE President config file with certificate parameters.")
	pflag.StringVar(&options.ViceCrtFile, "vice-cert", "/etc/vice-president/secrets/vice.cert", "A PEM encoded certificate file.")
	pflag.StringVar(&options.ViceKeyFile, "vice-key", "/etc/vice-president/secrets/vice.key", "A PEM encoded private key file.")
	pflag.StringVar(&options.IntermediateCertificate, "intermediate-cert", "/etc/vice-president/secrets/intermediate.cert", "A PEM encoded intermediate certificate.")
	pflag.StringVar(&options.RootCACertificate, "ca-cert", "/etc/vice-president/secrets/ca.cert", "A PEM encoded root CA certificate. (optional. will attempt to download if not found)")
	pflag.IntVar(&options.MinCertValidityDays, "min-cert-validity-days", 30, "Renew certificates that expire within n days.")
	pflag.BoolVar(&options.EnableValidateRemoteCertificate, "enable-validate-remote-cert", false, "Enable validation of remote certificate via TLS handshake.")
	pflag.IntVar(&options.MetricPort, "metric-port", 9091, "Port on which Prometheus metrics are exposed.")
	pflag.BoolVar(&options.IsEnableAdditionalSymantecMetrics, "enable-symantec-metrics", false, "Export additional symantec metrics.")
	pflag.BoolVar(&options.IsDebug, "debug", false, "Enable debug logging.")
	pflag.DurationVar(&options.CertificateCheckInterval, "certificate-recheck-interval", 5*time.Minute, "Interval for checking certificates.")
	pflag.DurationVar(&options.ResyncInterval, "resync-interval", 2*time.Minute, "Interval for resyncing informers.")
	pflag.IntVar(&options.RateLimit, "rate-limit", 2, "Rate limit of certificate enrollments per host. (unlimited: -1)")
	pflag.IntVar(&options.Threadiness, "threadiness", 10, "Operator threadiness.")
	pflag.StringVar(&options.Namespace, "namespace", "", "Limit operator to given namespace.")
	pflag.StringVar(&options.Finalizer, "finalizer", "vicepresident.extensions/v1beta1", "FinalizerVicePresident is the vice presidential finalizer for an ingress")
	pflag.StringVar(&options.EventComponent, "event-component", "vice-president", "Component to use for kubernetes events.")
	pflag.StringVar(&options.IngressAnnotation, "ingress-annotation", "vice-president", "Handle ingress' with this annotation.")
}

func main() {
	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	logger := log.NewLogger(options.IsDebug)

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	vp, err := president.New(options, logger)
	if err != nil {
		logger.LogFatal("fatal error while starting operator", "err", err)
		return
	}

	go vp.Run(options.Threadiness, stop, wg)
	go president.ExposeMetrics(options, stop, wg, logger)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	logger.LogInfo("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}
