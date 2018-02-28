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

// Options to configure the operator
type Options struct {
	KubeConfig                   string
	ConfigmapAnnotation          string
	PrometheusConfigMapNamespace string
	PrometheusConfigMapName      string
	MetricPort                   int
	ResyncPeriod                 int
	RecheckPeriod                int
	Threadiness                  int
	LogLevel                     int
}

// CheckOptions verifies the Options and sets default values, if necessary
func (o *Options) CheckOptions() error {
	if o.KubeConfig == "" {
		LogDebug("Path to kubeconfig not provided. Using Default")
	}
	if o.ConfigmapAnnotation == "" {
		LogDebug("Checking configmaps with annotation: %s", o.ConfigmapAnnotation)
	}
	return nil
}
