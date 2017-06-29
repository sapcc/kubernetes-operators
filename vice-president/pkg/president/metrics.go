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
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var enrollSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_enrollments",
		Help: "Counter for successful certificate enrollments.",
	},
	[]string{"ingress", "host"},
)

var enrollFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_enrollments",
		Help: "Counter for failed certificate enrollments.",
	},
	[]string{"ingress", "host"},
)

var renewSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_renewals",
		Help: "Counter for successful certificate renewals.",
	},
	[]string{"ingress", "host"},
)

var renewFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_renewals",
		Help: "Counter for failed certificate renewals.",
	},
	[]string{"ingress", "host"},
)

var pickupSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_pickups",
		Help: "Counter for successful certificate pickups.",
	},
	[]string{"ingress", "host"},
)

var pickupFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_pickups",
		Help: "Counter for failed certificate pickups.",
	},
	[]string{"ingress", "host"},
)

var approveSuccessCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_successful_approvals",
		Help: "Counter for successful certificate approvals.",
	},
	[]string{"ingress", "host"},
)

var approveFailedCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{
		Name: "vice_president_failed_approvals",
		Help: "Counter for failed certificate approvals.",
	},
	[]string{"ingress", "host"},
)

// init failure metrics with 0. useful for alerting.
func initializeFailureMetrics(labels map[string]string) {
	enrollFailedCounter.With(labels).Add(0.0)
	renewFailedCounter.With(labels).Add(0.0)
	approveFailedCounter.With(labels).Add(0.0)
	pickupFailedCounter.With(labels).Add(0.0)
}

func init() {
	prometheus.MustRegister(
		enrollSuccessCounter,
		enrollFailedCounter,
		renewSuccessCounter,
		renewFailedCounter,
		pickupSuccessCounter,
		pickupFailedCounter,
		approveSuccessCounter,
		approveFailedCounter,
	)
}

// ExposeMetrics exposes the above defined metrics on <metricPort>:/metrics
func ExposeMetrics(metricPort string) error {
	http.Handle("/metrics", promhttp.Handler())
	LogInfo("Exposing metrics on localhost:%s/metrics ",metricPort)
	return http.ListenAndServe(metricPort, nil)
}
