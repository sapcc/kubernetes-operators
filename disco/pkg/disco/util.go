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

package disco

import (
	"fmt"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
	"strings"

	"github.com/gophercloud/gophercloud/openstack/dns/v2/zones"

	"k8s.io/api/extensions/v1beta1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func newClientConfig(options Options) (*rest.Config, error) {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}
	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}
	return clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
}

func ingressHasDiscoFinalizer(ingress *v1beta1.Ingress) bool {
	for _, fin := range ingress.GetFinalizers() {
		if fin == DiscoFinalizer {
			return true
		}
	}
	return false
}

func ingressHasDeletionTimestamp(ingress *v1beta1.Ingress) bool {
	if ingress.GetDeletionTimestamp() != nil {
		return true
	}
	return false
}

// addSuffixIfRequired ensures the recordset name ends with '.'
func addSuffixIfRequired(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}

func mergeMaps(src, dst map[string]string) map[string]string {
	if src == nil {
		return dst
	}
	if dst == nil {
		return src
	}
	for k, v := range src {
		dst[k] = v
	}
	return dst
}

func trimQuotesAndSpace(s string) string {
	if s == "" {
		return s
	}
	st := strings.Trim(s, `"`)
	return strings.TrimSpace(st)
}

func ingressKey(ing *v1beta1.Ingress) string {
	return fmt.Sprintf("%s/%s", ing.GetNamespace(), ing.GetName())
}

func zoneListToString(zonesList []zones.Zone) string {
	zoneNameList := make([]string, 0)
	for _, z := range zonesList {
		zoneNameList = append(zoneNameList, z.Name)
	}
	return strings.Join(zoneNameList, ", ")
}

func recordSetListToString(rsList []recordsets.RecordSet) string {
	rsNameList := make([]string, 0)
	for _, rs := range rsList {
		rsNameList = append(rsNameList, rs.Name)
	}
	return strings.Join(rsNameList, ", ")
}
