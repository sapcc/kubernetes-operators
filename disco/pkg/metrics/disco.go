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

package disco

import (
	"fmt"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
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

var (
	recordsetCreationSuccessCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: MetricNamespace,
			Subsystem: MetricRecordset,
			Name:      "successful_creations",
			Help:      "Counter for successful recordset creations",
		},
		[]string{"ingress", "host"},
	)

	recordsetCreationFailedCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: MetricNamespace,
			Subsystem: MetricRecordset,
			Name:      "failed_creations",
			Help:      "Counter for failed recordset creations.",
		},
		[]string{"ingress", "host"},
	)

	recordsetDeletionSuccessCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: MetricNamespace,
			Subsystem: MetricRecordset,
			Name:      "succesful_deletions",
			Help:      "Counter for successful recordset deletions",
		},
		[]string{"ingress", "host"},
	)

	recordsetDeletionFailedCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: MetricNamespace,
			Subsystem: MetricRecordset,
			Name:      "failed_deletions",
			Help:      "Counter for failed recordset deletions",
		},
		[]string{"ingress", "host"},
	)
)

func registerCollectors() {
	prometheus.MustRegister(
		recordsetCreationSuccessCounter,
		recordsetCreationFailedCounter,
		recordsetDeletionSuccessCounter,
		recordsetDeletionFailedCounter,
	)
}

// ExposeMetrics exposes the above defined metrics on <host>:<metricPort>/metrics
func ExposeMetrics(host string, metricPort int, stopCh <-chan struct{}, wg *sync.WaitGroup, logger log.Logger) {
	logger = log.NewLoggerWith(logger, "component", "metrics")

	wg.Add(1)
	defer wg.Done()

	registerCollectors()
	ln, err := net.Listen("tcp", fmt.Sprintf("%v:%v", host, metricPort))
	if err != nil {
		logger.LogError("error exposing metrics", err)
		return
	}
	logger.LogInfo("Exposing metrics", "host", host, "port", metricPort)
	go http.Serve(ln, promhttp.Handler())
	<-stopCh
	ln.Close()
}
