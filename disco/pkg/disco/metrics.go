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

package disco

import (
	"fmt"
	"net"
	"net/http"
	"sync"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	// MetricNamespace used to prefix metrics
	MetricNamespace = "disco"
	// MetricRecordset used to prefix metrics
	MetricRecordset = "recordsets"
)

var recordsetCreationSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Subsystem: MetricRecordset,
		Name:      "successful_creations",
		Help:      "Counter for successful recordset creations",
	},
	[]string{"ingress", "host"},
)

var recordsetCreationFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Subsystem: MetricRecordset,
		Name:      "failed_creations",
		Help:      "Counter for failed recordset creations.",
	},
	[]string{"ingress", "host"},
)

// init failure metrics with 0. useful for alerting.
func initializeFailureMetrics(labels map[string]string) {
	recordsetCreationFailedCounter.With(labels).Add(0.0)
}

func registerCollectors() {
	prometheus.MustRegister(
		recordsetCreationSuccessCounter,
		recordsetCreationFailedCounter,
	)
}

// ExposeMetrics exposes the above defined metrics on <host>:<metricPort>/metrics
func ExposeMetrics(host string, metricPort int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	wg.Add(1)
	defer wg.Done()
	registerCollectors()
	ln, err := net.Listen("tcp", fmt.Sprintf("%v:%v", host, metricPort))
	if err != nil {
		LogInfo("Failed to expose metrics: %#v", err)
		return
	}
	go http.Serve(ln, promhttp.Handler())
	<-stopCh
	ln.Close()
}
