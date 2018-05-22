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
	"fmt"
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	// MetricNamespace used as prefix for metrics
	MetricNamespace = "vice_president"
)

var enrollSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "successful_enrollments",
		Help:      "Counter for successful certificate enrollments.",
	},
	[]string{"ingress", "host", "sans"},
)

var enrollFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "failed_enrollments",
		Help:      "Counter for failed certificate enrollments.",
	},
	[]string{"ingress", "host", "sans"},
)

var renewSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "successful_renewals",
		Help:      "Counter for successful certificate renewals.",
	},
	[]string{"ingress", "host", "sans"},
)

var renewFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "failed_renewals",
		Help:      "Counter for failed certificate renewals.",
	},
	[]string{"ingress", "host", "sans"},
)

var pickupSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "successful_pickups",
		Help:      "Counter for successful certificate pickups.",
	},
	[]string{"ingress", "host", "sans"},
)

var pickupFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "failed_pickups",
		Help:      "Counter for failed certificate pickups.",
	},
	[]string{"ingress", "host", "sans"},
)

var approveSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "successful_approvals",
		Help:      "Counter for successful certificate approvals.",
	},
	[]string{"ingress", "host", "sans"},
)

var approveFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "failed_approvals",
		Help:      "Counter for failed certificate approvals.",
	},
	[]string{"ingress", "host", "sans"},
)

var replaceSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "successful_replacements",
		Help:      "Counter for successful certificate replacements.",
	},
	[]string{"ingress", "host", "sans"},
)

var replaceFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Namespace: MetricNamespace,
		Name:      "failed_replacements",
		Help:      "Counter for failed certificate replacements.",
	},
	[]string{"ingress", "host", "sans"},
)

var apiRateLimitHitGauge = prometheus.NewGaugeVec(
	prometheus.GaugeOpts{
		Namespace: MetricNamespace,
		Name:      "rate_limit_reached",
		Help:      "Maximum number of VICE API requests within 1h reached",
	},
	[]string{"ingress", "host", "sans"},
)

// init failure metrics with 0. useful for alerting.
func initializeFailureMetrics(labels map[string]string) {
	enrollFailedCounter.With(labels).Add(0.0)
	renewFailedCounter.With(labels).Add(0.0)
	approveFailedCounter.With(labels).Add(0.0)
	pickupFailedCounter.With(labels).Add(0.0)
	replaceFailedCounter.With(labels).Add(0.0)
}

func registerCollectors(collector prometheus.Collector) {
	if collector != nil {
		prometheus.MustRegister(collector)
	}
	prometheus.MustRegister(
		enrollSuccessCounter,
		enrollFailedCounter,
		renewSuccessCounter,
		renewFailedCounter,
		pickupSuccessCounter,
		pickupFailedCounter,
		approveSuccessCounter,
		approveFailedCounter,
		replaceSuccessCounter,
		replaceFailedCounter,
		apiRateLimitHitGauge,
	)
}

// ExposeMetrics exposes the above defined metrics on <metricPort>:/metrics
func ExposeMetrics(metricPort int, isEnableAdditionalSymantecMetrics bool, viceCertFilePath, viceKeyFilePath string) error {
	if isEnableAdditionalSymantecMetrics {
		registerCollectors(NewSymantecMetricsCollector(viceCertFilePath, viceKeyFilePath))
	} else {
		registerCollectors(nil)
	}
	http.Handle("/metrics", promhttp.Handler())
	LogInfo("Exposing metrics on localhost:%v/metrics ", metricPort)
	return http.ListenAndServe(
		fmt.Sprintf("0.0.0.0:%v", metricPort),
		nil,
	)
}
