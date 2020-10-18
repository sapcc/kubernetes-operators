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

package config

import (
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
)

// Options to configure your disco operator
type Options struct {
	KubeConfig,
	ConfigPath,
	Record,
	ZoneName,
	EventComponent,
	IngressAnnotation,
	ServiceAnnotation,
	Finalizer,
	MetricHost string
	Threadiness,
	MetricPort,
	RecordsetTTL int
	ResyncPeriod,
	RecheckPeriod time.Duration
	IsDebug,
	IsInstallCRD bool
}

func (o *Options) applyDefaultsIfNotSet() {
	o.IngressAnnotation = trimQuotesAndSpace(o.IngressAnnotation)
	o.ServiceAnnotation = trimQuotesAndSpace(o.ServiceAnnotation)
	o.ZoneName = trimQuotesAndSpace(o.ZoneName)
	o.Record = trimQuotesAndSpace(o.Record)
}

// CheckOptions verifies the Options and sets default values, if necessary
func (o *Options) CheckOptions(logger log.Logger) error {
	if o.ConfigPath == "" {
		return errors.New("Path to disco config not provided. Aborting")
	}
	if o.KubeConfig == "" {
		logger.LogDebug("Path to kubeconfig not provided. Using Default")
	}
	if o.Finalizer == "" {
		return errors.New("finalizer can't be empty")
	}
	o.applyDefaultsIfNotSet()
	return nil
}

func trimQuotesAndSpace(s string) string {
	if s == "" {
		return s
	}
	st := strings.Trim(s, `"`)
	return strings.TrimSpace(st)
}
