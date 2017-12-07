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

package president

import (
	"context"
	"crypto/tls"
	"fmt"
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sapcc/go-vice"
)

var enrollSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_enrollments",
		Help: "Counter for successful certificate enrollments.",
	},
	[]string{"ingress", "host", "sans"},
)

var enrollFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_enrollments",
		Help: "Counter for failed certificate enrollments.",
	},
	[]string{"ingress", "host", "sans"},
)

var renewSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_renewals",
		Help: "Counter for successful certificate renewals.",
	},
	[]string{"ingress", "host", "sans"},
)

var renewFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_renewals",
		Help: "Counter for failed certificate renewals.",
	},
	[]string{"ingress", "host", "sans"},
)

var pickupSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_pickups",
		Help: "Counter for successful certificate pickups.",
	},
	[]string{"ingress", "host", "sans"},
)

var pickupFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_pickups",
		Help: "Counter for failed certificate pickups.",
	},
	[]string{"ingress", "host", "sans"},
)

var approveSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_approvals",
		Help: "Counter for successful certificate approvals.",
	},
	[]string{"ingress", "host", "sans"},
)

var approveFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_approvals",
		Help: "Counter for failed certificate approvals.",
	},
	[]string{"ingress", "host", "sans"},
)

var tokenCountOrderedGauge = prometheus.NewGaugeVec(
	prometheus.GaugeOpts{
		Name: "vice_president_ordered_tokens",
		Help: "Number of available certificate units",
	},
	[]string{"type"},
)

var tokenCountUsedGauge = prometheus.NewGaugeVec(
	prometheus.GaugeOpts{
		Name: "vice_president_used_tokens",
		Help: "Number of available certificate units",
	},
	[]string{"type"},
)

var tokenCountRemainingGauge = prometheus.NewGaugeVec(
	prometheus.GaugeOpts{
		Name: "vice_president_remaining_tokens",
		Help: "Number of available certificate units",
	},
	[]string{"type"},
)

// MetricsCollector ..
type MetricsCollector struct {
	viceClient *vice.Client
}

// NewMetricsCollector returns a new MetricsCollector
func NewMetricsCollector(viceCertFilePath, viceKeyFilePath string) *MetricsCollector {
	cert, err := tls.LoadX509KeyPair(viceCertFilePath, viceKeyFilePath)
	if err != nil {
		LogFatal("Couldn't load certificate from %s and/or key from %s for vice client: %v", viceCertFilePath, viceKeyFilePath, err)
	}
	return &MetricsCollector{
		viceClient: vice.New(cert),
	}
}

// Describe ..
func (m *MetricsCollector) Describe(ch chan<- *prometheus.Desc) {
	tokenCountOrderedGauge.Describe(ch)
	tokenCountRemainingGauge.Describe(ch)
	tokenCountUsedGauge.Describe(ch)
}

// Collect ..
func (m *MetricsCollector) Collect(ch chan<- prometheus.Metric) {
	desCh := make(chan *prometheus.Desc, 1)
	tokenCountRemainingGauge.Describe(desCh)
	tokenCountRemainingDesc := <-desCh
	tokenCountUsedGauge.Describe(desCh)
	tokenCountUsedDesc := <-desCh
	tokenCountOrderedGauge.Describe(desCh)
	tokenCountOrderedDesc := <-desCh

	tokenCount, err := m.viceClient.Certificates.GetTokenCount(context.TODO())
	if err != nil {
		LogError("Unable to fetch token count: %v", err)
	}
	if tokenCount == nil || tokenCount.Tokens == nil {
		LogError("Fetched Token count could'nt parse it %#v",tokenCount)
		return
	}

	for _, t := range tokenCount.Tokens {
		if t.Ordered == 0 && t.Used == 0 && t.Remaining == 0 {
			LogDebug("Token count for %#v is 0", t)
		} else {
			LogDebug("Got token count for %#v", t)

			ch <- prometheus.MustNewConstMetric(
				tokenCountRemainingDesc,
				prometheus.GaugeValue,
				float64(t.Remaining),
				string(t.Type),
			)

			ch <- prometheus.MustNewConstMetric(
				tokenCountUsedDesc,
				prometheus.GaugeValue,
				float64(t.Used),
				string(t.Type),
			)

			ch <- prometheus.MustNewConstMetric(
				tokenCountOrderedDesc,
				prometheus.GaugeValue,
				float64(t.Ordered),
				string(t.Type),
			)
		}
	}

}

// init failure metrics with 0. useful for alerting.
func initializeFailureMetrics(labels map[string]string) {
	enrollFailedCounter.With(labels).Add(0.0)
	renewFailedCounter.With(labels).Add(0.0)
	approveFailedCounter.With(labels).Add(0.0)
	pickupFailedCounter.With(labels).Add(0.0)
}

func registerCollectors(collector prometheus.Collector) {
	prometheus.MustRegister(
		enrollSuccessCounter,
		enrollFailedCounter,
		renewSuccessCounter,
		renewFailedCounter,
		pickupSuccessCounter,
		pickupFailedCounter,
		approveSuccessCounter,
		approveFailedCounter,
		collector,
	)
}

// ExposeMetrics exposes the above defined metrics on <metricPort>:/metrics
func ExposeMetrics(metricPort int, viceCertFilePath, viceKeyFilePath string) error {
	registerCollectors(NewMetricsCollector(viceCertFilePath, viceKeyFilePath))
	http.Handle("/metrics", promhttp.Handler())
	LogInfo("Exposing metrics on localhost:%v/metrics ", metricPort)
	return http.ListenAndServe(
		fmt.Sprintf("0.0.0.0:%v", metricPort),
		nil,
	)
}
