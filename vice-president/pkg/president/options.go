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
)

// Options to configure your vice president
type Options struct {
	KubeConfig          string
	VicePresidentConfig string

	ViceKeyFile string
	ViceCrtFile string

	IngressAnnotation string

	MetricListenAddress string
}

// CheckOptions verifies the Options and sets default values, if necessary
func (o *Options) CheckOptions() error {
	if o.ViceCrtFile == "" {
		return fmt.Errorf("Path to vice certificate not provided. Aborting")
	}
	if o.ViceKeyFile == "" {
		return fmt.Errorf("Path to vice key not provided. Aborting")
	}
	if o.VicePresidentConfig == "" {
		return fmt.Errorf("Path to vice config not provided. Aborting")
	}
	if o.KubeConfig == "" {
		LogDebug("Path to kubeconfig not provided. Using Default")
	}
	if o.IngressAnnotation == "" {
		o.IngressAnnotation = "vice-president"
		LogDebug("Ingress annotation not provided. Using default 'vice-president'.")
	}

	if o.MetricListenAddress == "" {
		o.MetricListenAddress = "9091"
		LogDebug("Metric listen address not provided. Using default :9091/metrics.")
	}

	return nil
}
