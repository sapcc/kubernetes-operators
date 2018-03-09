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

import "github.com/pkg/errors"

// Options to configure your disco operator
type Options struct {
	KubeConfig        string
	ConfigPath        string
	IngressAnnotation string
	Threadiness       int
	MetricPort        int
	ResyncPeriod      int
	RecheckPeriod     int
	RecordsetTTL      int
	Record            string
	ZoneName          string
}

func (o *Options) applyDefaultsIfNotSet() {
	if o.MetricPort == 0 {
		o.MetricPort = DefaultMetricPort
	}
	if o.IngressAnnotation == "" {
		o.IngressAnnotation = DefaultIngressAnnotation
	}
	if o.Threadiness <= 0 {
		o.Threadiness = 1
	}
}

// CheckOptions verifies the Options and sets default values, if necessary
func (o *Options) CheckOptions() error {
	if o.ConfigPath == "" {
		return errors.New("Path to disco config not provided. Aborting")
	}
	if o.KubeConfig == "" {
		LogDebug("Path to kubeconfig not provided. Using Default")
	}
	o.applyDefaultsIfNotSet()
	return nil
}
