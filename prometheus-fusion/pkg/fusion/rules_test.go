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

package fusion

import (
	"testing"

	"github.com/prometheus/prometheus/pkg/rulefmt"
	"github.com/stretchr/testify/assert"
)

const (
	GoodRuleGroup   = "groups:\n- name: prometheus\n  rules:\n  - record: prometheus_rate\n    expr: rate(prometheus_total[5m])"
	BadRuleGroup    = "groups:\n - name: foo\n   rules:\n   - record: foo_rate\n     sum(prometheus_total[5m])"
	RulesPrometheus = "prometheus.rules"

	AlertsCritical     = "critical.alerts"
	CriticalAlertGroup = "groups:\n- name: critical.alerts\n  rules:\n  - alert: CriticalAlert\n    expr: prometheus_total>1\n    for: 1h\n    labels:\n      context: foo\n    annotations:\n      description: bar"
)

func TestValidation(t *testing.T) {

	testData := map[string]string{
		"good.rules":      GoodRuleGroup,
		"bad.rules":       BadRuleGroup,
		"critical.alerts": CriticalAlertGroup,
	}

	for name, rule := range testData {
		err := validateRules(map[string]string{name: rule})

		switch rule {
		case GoodRuleGroup, CriticalAlertGroup:
			assert.Empty(t, err)
		case BadRuleGroup:
			assert.NotEmpty(t, err)
		}
	}
}

func TestFuseRuleGroups(t *testing.T) {
	promRg := &rulefmt.RuleGroups{
		Groups: []rulefmt.RuleGroup{
			{
				Name: "fuse.rules",
				Rules: []rulefmt.Rule{
					{
						Record: "prometheus_sum",
						Expr: "sum(prometheus)",
					},
				},
			},
		},
	}

	testRg := []*rulefmt.RuleGroups{
		{
			Groups: []rulefmt.RuleGroup{
				{
					Name: "fuse.rules",
					Rules: []rulefmt.Rule{
						{
							Record: "prometheus_rate",
							Expr: "rate(prometheus_total[5m])",
						},
					},
				},
			},
		},
		{
			Groups: []rulefmt.RuleGroup{
				{
					Name: "foo.rules",
					Rules: []rulefmt.Rule{
						{
							Record: "prometheus_rate",
							Expr: "rate(prometheus_total[5m])",
						},
					},
				},
			},
		},
	}

	expectedRg := []*rulefmt.RuleGroups{
		{
			Groups: []rulefmt.RuleGroup{
				{
					Name: "fuse.rules",
					Rules: []rulefmt.Rule{
						{
							Record: "prometheus_sum",
							Expr: "sum(prometheus)",
						},
						{
							Record: "prometheus_rate",
							Expr: "rate(prometheus_total[5m])",
						},
					},
				},
			},
		},
		{
			Groups: []rulefmt.RuleGroup{
				{
					Name: "fuse.rules",
					Rules: []rulefmt.Rule{
						{
							Record: "prometheus_sum",
							Expr: "sum(prometheus)",
						},
						{
							Record: "prometheus_rate",
							Expr: "rate(prometheus_total[5m])",
						},
					},
				},
				{
					Name: "foo.rules",
					Rules: []rulefmt.Rule{
						{
							Record: "prometheus_rate",
							Expr: "rate(prometheus_total[5m])",
						},
					},
				},
			},
		},
	}

	for k, rg := range testRg {
		errs := fuseRuleGroups(promRg,rg)
		assert.Empty(t, errs)
		assert.Equal(t, expectedRg[k], promRg)
	}
}

func TestParseValidateFuseAndMarshal(t *testing.T) {
	testData := []map[string]string{
		{
			RulesPrometheus: "groups:\n- name: fuse.rules\n  rules:\n  - record: prometheus_sum\n    expr: sum(prometheus)",
		},
		{
			AlertsCritical: CriticalAlertGroup,
		},
	}

	expectedData := []map[string]string{
		{
			RulesPrometheus: "groups:\n- name: fuse.rules\n  rules:\n  - record: prometheus_rate\n    expr: rate(prometheus_total[5m])\n  - record: prometheus_sum\n    expr: sum(prometheus)\n",
		},
		{
			RulesPrometheus: "groups:\n- name: fuse.rules\n  rules:\n  - record: prometheus_rate\n    expr: rate(prometheus_total[5m])",
			AlertsCritical: CriticalAlertGroup,
		},
	}

	for i,data := range testData {
		promCmData := map[string]string{
			RulesPrometheus: "groups:\n- name: fuse.rules\n  rules:\n  - record: prometheus_rate\n    expr: rate(prometheus_total[5m])",
		}

		errs := fuseMaps(promCmData,data)
		assert.Empty(t, errs)

		assert.Equal(t, expectedData[i], promCmData)

	}
}
