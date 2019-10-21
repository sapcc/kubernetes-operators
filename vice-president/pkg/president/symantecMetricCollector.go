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

package president

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/config"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/go-vice"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
)

const (
	tokenCountOrdered   = "token_count_ordered"
	tokenCountUsed      = "token_count_used"
	tokenCountRemaining = "token_count_remaining"
	organizationExpires = "organization_expires"
	ssoCertExpires      = "sso_certificate_expires"
)

// SymantecMetricsCollector ..
type SymantecMetricsCollector struct {
	prometheus.Collector

	viceClient     *vice.Client
	ssoCertificate *x509.Certificate
	metrics        map[string]*prometheus.Desc
	logger         log.Logger
}

// NewSymantecMetricsCollector returns a new collector for Symantec metrics.
func NewSymantecMetricsCollector(options config.Options, logger log.Logger) *SymantecMetricsCollector {
	cert, err := tls.LoadX509KeyPair(options.ViceCrtFile, options.ViceKeyFile)
	if err != nil {
		logger.LogFatal("couldn't load sso certificate", "cert path", options.ViceCrtFile, "key path", options.ViceKeyFile, "err", err)
	}

	certX509, err := readCertFromFile(options.ViceCrtFile)
	if err != nil {
		logger.LogFatal("couldn't load sso certificate", "cert path", options.ViceCrtFile, "key path", options.ViceKeyFile, "err", err)
	}

	return &SymantecMetricsCollector{
		viceClient:     vice.New(cert),
		logger:         logger,
		ssoCertificate: certX509,
		metrics: map[string]*prometheus.Desc{
			tokenCountOrdered:   newTokenCountMetricDesc("ordered", "The number of ordered certificate units.", []string{"type"}),
			tokenCountUsed:      newTokenCountMetricDesc("used", "The number of used certificate units.", []string{"type"}),
			tokenCountRemaining: newTokenCountMetricDesc("remaining", "The number of remaining certificate units.", []string{"type"}),
			organizationExpires: newOrgMetricDesc("expires", "The Symantec organization expiration date.", []string{"name", "status", "auth_status"}),
			ssoCertExpires:      newSSOCertExpiresDesc("expires", "The expiry of the SSO certificate in unix time."),
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

func newSSOCertExpiresDesc(metricName, docString string) *prometheus.Desc {
	return prometheus.NewDesc(
		prometheus.BuildFQName(MetricNamespace, "sso_certificate", metricName),
		docString,
		nil,
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

	// Check the SSO certificate expiry.
	ch <- prometheus.MustNewConstMetric(
		m.metrics[ssoCertExpires],
		prometheus.GaugeValue,
		float64(m.ssoCertificate.NotAfter.Unix()),
	)
	if !time.Now().UTC().Before(m.ssoCertificate.NotAfter.UTC()) {
		m.logger.LogInfo("the sso certificate expired", "notAfter", m.ssoCertificate.NotAfter.UTC().String())
	}

	// Get the number of used and available Symantec tokens.
	tokenCount, err := m.viceClient.Certificates.GetTokenCount(context.TODO())
	if err != nil {
		m.logger.LogError("unable to fetch token count", err)
		return
	}
	if tokenCount == nil || tokenCount.Tokens == nil {
		m.logger.LogInfo("fetched Token count could'nt parse it", "tokens", tokenCount)
		return
	}

	for _, t := range tokenCount.Tokens {
		if t.Ordered == 0 && t.Used == 0 && t.Remaining == 0 {
			m.logger.LogDebug("token count is 0", "product type", t.Type)
		} else {
			m.logger.LogDebug("got token count", "count", t)

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

	// Gets the expiry of the Organization in Symantec.
	o, err := m.viceClient.Certificates.GetOrganizationInfo(context.TODO())
	if err != nil {
		m.logger.LogError("unable to fetch symantec organization information", err)
		return
	}
	if o == nil {
		m.logger.LogInfo("unable to parse symantec org info")
		return
	}

	org := o.Organization
	if isAnyStringEmpty(org.Name, org.OrgStatus, org.AuthStatus) {
		m.logger.LogInfo("unable to parse some values from symatec org")
		return
	}

	m.logger.LogDebug("got org info", fmt.Sprintf("%v", org))
	ch <- prometheus.MustNewConstMetric(
		m.metrics[organizationExpires],
		prometheus.GaugeValue,
		float64(org.AuthExpires.Unix()),
		org.Name,
		org.OrgStatus,
		org.AuthStatus,
	)
}
