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
	"strings"
	"unicode"

	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/zones"
	v1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco/v1"
	coreV1 "k8s.io/api/core/v1"
	"k8s.io/api/extensions/v1beta1"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/tools/cache"
)

// recordHelper struct used to wrap ingress, service and discoRecord CRD.
type recordHelper struct {
	recordType  string
	records     []string
	zoneName    string
	description string
	object      runtime.Object
}

func splitFunc(c rune) bool {
	return !unicode.IsLetter(c) && !unicode.IsNumber(c) && c != '.' && c != '_' && c != '-'
}

func newDefaultRecordHelper(record, zoneName string) *recordHelper {
	return &recordHelper{
		recordType:  RecordsetType.CNAME,
		records:     strings.FieldsFunc(record, splitFunc),
		zoneName:    zoneName,
		description: discoRecordsetDescription,
	}
}

func (r *recordHelper) getKey() string {
	if key, err := keyFunc(r.object); err == nil {
		return key
	}
	return ""
}

func (r *recordHelper) getKind() string {
	objMeta, err := meta.TypeAccessor(r.object)
	if err != nil || objMeta.GetKind() == "" {
		switch r.object.(type) {
		case *v1beta1.Ingress:
			return "ingress"
		case *coreV1.Service:
			return "service"
		case *v1.Record:
			return "record"
		}

		return ""
	}
	return strings.ToLower(objMeta.GetKind())
}

func keyFunc(obj interface{}) (string, error) {
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		return "", err
	}

	typeMeta, err := meta.TypeAccessor(obj)
	if err != nil {
		return "", nil
	}

	var kind string
	k := typeMeta.GetKind()
	if k == "Ingress" || k == "Service" || k == v1.RecordKind {
		kind = strings.ToLower(k)
	} else {
		switch obj.(type) {
		case *v1beta1.Ingress:
			kind = "ingress"
		case *coreV1.Service:
			kind = "service"
		case *v1.Record:
			kind = "record"
		default:
			kind = ""
		}
	}

	if kind == "" {
		return "", fmt.Errorf("unkown kind: %s", kind)
	}

	return fmt.Sprintf("%s/%s", kind, key), nil
}

func splitKeyFunc(key string) (objType, namespace, name string, err error) {
	parts := strings.Split(key, "/")
	parts = filterEmpty(parts)
	switch len(parts) {
	case 2:
		return "", parts[0], parts[1], nil
	case 3:
		return parts[0], parts[1], parts[2], nil
	}

	return "", "", "", fmt.Errorf("unexpected key format: %q", key)
}

func splitKeyFuncWithObjKind(k string) (objKind, key string, err error) {
	objKind, namespace, name, err := splitKeyFunc(k)
	if err != nil {
		return "", "", err
	}
	return objKind, fmt.Sprintf("%s/%s", namespace, name), nil
}

func filterEmpty(sslice []string) []string {
	var filteredSlice []string
	for _, itm := range sslice {
		if itm != "" {
			filteredSlice = append(filteredSlice, itm)
		}
	}
	return filteredSlice
}

// ensureFQDN ensures the recordset name ends with '.'
func ensureFQDN(s string) string {
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

func makeAnnotation(prefix, annotation string) string {
	const slash = "/"
	prefix = strings.TrimSuffix(prefix, slash)
	annotation = strings.TrimPrefix(annotation, slash)
	return fmt.Sprintf("%s/%s", prefix, annotation)
}

func isSliceContainsStr(sl []string, str string) bool {
	for _, s := range sl {
		if s == str {
			return true
		}
	}
	return false
}
