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

	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/go-vice"
)

const (
	tokenCountOrdered   = "token_count_ordered"
	tokenCountUsed      = "token_count_used"
	tokenCountRemaining = "token_count_remaining"
	organizationExpires = "organization_expires"
)

// SymantecMetricsCollector ..
type SymantecMetricsCollector struct {
	prometheus.Collector
	viceClient *vice.Client

	metrics map[string]*prometheus.Desc
}

// NewSymantecMetricsCollector returns a new collector for symantec metrics
func NewSymantecMetricsCollector(viceCertFilePath, viceKeyFilePath string) *SymantecMetricsCollector {
	cert, err := tls.LoadX509KeyPair(viceCertFilePath, viceKeyFilePath)
	if err != nil {
		LogFatal("Couldn't load certificate from %s and/or key from %s for vice client: %v", viceCertFilePath, viceKeyFilePath, err)
	}

	return &SymantecMetricsCollector{
		viceClient: vice.New(cert),
		metrics: map[string]*prometheus.Desc{
			tokenCountOrdered:   newTokenCountMetricDesc("ordered", "Number of ordered certificate units", []string{"type"}),
			tokenCountUsed:      newTokenCountMetricDesc("used", "Number of used certificate units", []string{"type"}),
			tokenCountRemaining: newTokenCountMetricDesc("remaining", "Number of remaining certificate units", []string{"type"}),
			organizationExpires: newOrgMetricDesc("expires", "Symantec organization expiration date", []string{"name", "status", "auth_status"}),
		},
	}
}

func newTokenCountMetricDesc(metricName, docString string, labels []string) *prometheus.Desc {
	return newMetricDesc("token_count", metricName, docString, labels)
}

func newOrgMetricDesc(metricName, docString string, labels []string) *prometheus.Desc {
	return newMetricDesc("organization", metricName, docString, labels)
}

func newMetricDesc(subSystem, metricName, docString string, labels []string) *prometheus.Desc {
	return prometheus.NewDesc(
		prometheus.BuildFQName(MetricNamespace, subSystem, metricName),
		docString,
		labels,
		nil,
	)
}

// Describe ..
func (m *SymantecMetricsCollector) Describe(ch chan<- *prometheus.Desc) {
	for _, metric := range m.metrics {
		ch <- metric
	}
}

// Collect ..
func (m *SymantecMetricsCollector) Collect(ch chan<- prometheus.Metric) {

	// getTokenCount
	tokenCount, err := m.viceClient.Certificates.GetTokenCount(context.TODO())
	if err != nil {
		LogError("Unable to fetch token count: %v", err)
	}
	if tokenCount == nil || tokenCount.Tokens == nil {
		LogError("Fetched Token count could'nt parse it %#v", tokenCount)
	}

	// getOrgInfo
	o, err := m.viceClient.Certificates.GetOrganizationInfo(context.TODO())
	if err != nil {
		LogError("Unable to fetch symantec organization information: %v", err)
	}
	if o == nil {
		LogError("Unable to parse symantec org info")
	}

	for _, t := range tokenCount.Tokens {
		if t.Ordered == 0 && t.Used == 0 && t.Remaining == 0 {
			LogDebug("Token count for %#v is 0", t)
		} else {
			LogDebug("Got token count for %#v", t)

			ch <- prometheus.MustNewConstMetric(
				m.metrics[tokenCountOrdered],
				prometheus.GaugeValue,
				float64(t.Ordered),
				string(t.Type),
			)

			ch <- prometheus.MustNewConstMetric(
				m.metrics[tokenCountUsed],
				prometheus.GaugeValue,
				float64(t.Used),
				string(t.Type),
			)

			ch <- prometheus.MustNewConstMetric(
				m.metrics[tokenCountRemaining],
				prometheus.GaugeValue,
				float64(t.Remaining),
				string(t.Type),
			)
		}
	}

	org := o.Organization
	if isAnyStringEmpty(org.Name, org.OrgStatus, org.AuthStatus) {
		LogError("Unable to parse some values from symatec org")
	} else {
		LogDebug("Got org info: %#v", org)
		ch <- prometheus.MustNewConstMetric(
			m.metrics[organizationExpires],
			prometheus.GaugeValue,
			float64(org.AuthExpires.Unix()),
			org.Name,
			org.OrgStatus,
			org.AuthStatus,
		)
	}
}
