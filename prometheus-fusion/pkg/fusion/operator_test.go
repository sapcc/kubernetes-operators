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

//import (
//	"testing"
//	"time"
//
//  "github.com/stretchr/testify/assert"
//  corev1 "k8s.io/api/core/v1"
//	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
//	"k8s.io/client-go/informers/core/v1"
//	"k8s.io/client-go/kubernetes/fake"
//	"k8s.io/client-go/tools/cache"
//	"k8s.io/client-go/util/workqueue"
//)
//
//const (
//	NAMESPACE     = "default"
//	CMNAME        = "shark"
//	RESYNPERIOD   = 1 * time.Minute
//	RECHECKPERIOD = 5 * time.Second
//)
//
//func newPrometheusConfigMap() *corev1.ConfigMap {
//	return &corev1.ConfigMap{
//		ObjectMeta: metav1.ObjectMeta{
//			Namespace: NAMESPACE,
//			Name:      "prometheus",
//		},
//		Data: map[string]string{
//		  "k8s.rules": "alotofrules",
//    },
//	}
//}
//
//func newSourceConfigMap() *corev1.ConfigMap {
//	return &corev1.ConfigMap{
//		ObjectMeta: metav1.ObjectMeta{
//			Namespace: NAMESPACE,
//			Name:      CMNAME,
//		},
//		Data: map[string]string{
//			"prometheus.rules": "A",
//		},
//	}
//}
//
//func newOperator() *Operator {
//	fakeClientSet := fake.NewSimpleClientset(newPrometheusConfigMap())
//
//	cmInformer := v1.NewConfigMapInformer(
//		fakeClientSet,
//		"",
//		RESYNPERIOD,
//		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
//	)
//
//	return &Operator{
//	  Options: Options{
//	    PrometheusConfigMapNamespace: NAMESPACE,
//	    PrometheusConfigMapName: "prometheus",
//	    Threadiness: 1,
//    },
//		clientset:     fakeClientSet,
//		cmInformer:    cmInformer,
//		ResyncPeriod:  RESYNPERIOD,
//		RecheckPeriod: RECHECKPERIOD,
//		queue:         workqueue.NewRateLimitingQueue(workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second)),
//	}
//}
//
//func TestConfigMapMerge(t *testing.T) {
//	o := newOperator()
//	assert.NoError(t, o.checkContainsOrMergeRulesAndUpdateUpstream(newSourceConfigMap()))
//}
