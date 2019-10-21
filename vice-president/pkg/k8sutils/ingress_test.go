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

package k8sutils

import (
	"testing"

	"github.com/stretchr/testify/assert"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func createIngress() *extensionsv1beta1.Ingress {
	return &extensionsv1beta1.Ingress{
		ObjectMeta: metaV1.ObjectMeta{
			Namespace: "default",
			Name:      "myIngress",
			Annotations: map[string]string{
				"vice-president":              "true",
				"vice-president/replace-cert": "true",
			},
		},
		Spec: extensionsv1beta1.IngressSpec{
			TLS: []extensionsv1beta1.IngressTLS{
				{
					Hosts:      []string{"a.com"},
					SecretName: "tls-a-com",
				},
				{
					Hosts:      []string{"b.com"},
					SecretName: "tls-b-com",
				},
				{
					Hosts:      []string{"lasthost.com", "foobar.com"},
					SecretName: "tls-lasthost-com",
				},
			},
		},
	}
}

func TestIsLastHostInIngressSpec(t *testing.T) {
	lastHost := "lasthost.com"
	ingress := createIngress()

	assert.False(t, IsLastHostInIngressSpec(ingress, ""), "is not the last host in the ingress spec")
	assert.Truef(t, IsLastHostInIngressSpec(ingress, lastHost), "'%s' is the last host in the ingress.spec.tls", lastHost)
}

func TestIsCertificateForHostShouldBeReplaced(t *testing.T) {
	assert.True(t, IngressHasAnnotation(createIngress(), "vice-president/replace-cert"))
}
