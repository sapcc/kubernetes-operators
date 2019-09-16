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
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func (s *TestSuite) TestIsLastHostInIngressSpec() {
	LastHost := "lastHost.com"

	ingress := &extensionsv1beta1.Ingress{
		ObjectMeta: metaV1.ObjectMeta{
			Namespace: Namespace,
			Name:      IngressName,
			Annotations: map[string]string{
				"vice-president": "true",
			},
		},
		Spec: extensionsv1beta1.IngressSpec{
			TLS: []extensionsv1beta1.IngressTLS{
				{
					Hosts:      []string{HostName},
					SecretName: SecretName,
				},
				{
					Hosts:      []string{"foobar.com"},
					SecretName: "foosecret",
				},
				{
					Hosts:      []string{LastHost, "foobar.com"},
					SecretName: "lastSecret",
				},
			},
		},
	}

	s.False(isLastHostInIngressSpec(ingress, HostName), "is not the last host in the ingress spec")
	s.True(isLastHostInIngressSpec(ingress, LastHost), "'%s' is the last host in the ingress.spec.tls", LastHost)
}

func (s *TestSuite) TestIsCertificateForHostShouldBeReplaced() {
	testData := map[*extensionsv1beta1.Ingress]bool{
		{
			ObjectMeta: metaV1.ObjectMeta{
				Namespace: Namespace,
				Name:      IngressName,
				Annotations: map[string]string{
					"vice-president":              "true",
					"vice-president/replace-cert": "true",
				},
			},
			Spec: extensionsv1beta1.IngressSpec{
				TLS: []extensionsv1beta1.IngressTLS{
					{
						Hosts:      []string{HostName},
						SecretName: SecretName,
					},
				},
			},
		}: true,
		{
			ObjectMeta: metaV1.ObjectMeta{
				Namespace: Namespace,
				Name:      IngressName,
				Annotations: map[string]string{
					"vice-president": "true",
				},
			},
			Spec: extensionsv1beta1.IngressSpec{
				TLS: []extensionsv1beta1.IngressTLS{
					{
						Hosts:      []string{HostName},
						SecretName: SecretName,
					},
				},
			},
		}: false,
	}

	for ingress, expectedBool := range testData {
		s.Equal(expectedBool, isIngressHasAnnotation(ingress, AnnotationCertificateReplacement))
	}
}

func (s *TestSuite) TestIngressVicePresidentialAnnotation() {
	testData := map[*extensionsv1beta1.Ingress]bool{
		{
			ObjectMeta: metaV1.ObjectMeta{
				Namespace: Namespace,
				Name:      "DoNotIgnoreMe!",
				Annotations: map[string]string{
					"vice-president": "true",
				},
			},
		}: true,
		{
			ObjectMeta: metaV1.ObjectMeta{
				Namespace:   Namespace,
				Name:        "IgnoreMe!",
				Annotations: map[string]string{},
			},
		}: false,
	}

	for ingress, expectedBool := range testData {
		s.Equal(expectedBool, isIngressHasAnnotation(ingress, AnnotationVicePresident))
	}
}

func (s *TestSuite) TestIsIngressNeedsUpdate() {
	iOld := &extensionsv1beta1.Ingress{
		ObjectMeta: metaV1.ObjectMeta{
			Namespace: Namespace,
			Name:      "DoNotIgnoreMe!",
			Annotations: map[string]string{
				"vice-president":              "true",
				"vice-president/replace-cert": "true",
			},
		},
		Spec: extensionsv1beta1.IngressSpec{
			TLS: []extensionsv1beta1.IngressTLS{
				{
					Hosts:      []string{HostName},
					SecretName: SecretName,
				},
			},
		},
	}

	iCur := &extensionsv1beta1.Ingress{
		ObjectMeta: metaV1.ObjectMeta{
			Namespace: Namespace,
			Name:      "DoNotIgnoreMe!",
			Annotations: map[string]string{
				"vice-president": "true",
			},
		},
		Spec: extensionsv1beta1.IngressSpec{
			TLS: []extensionsv1beta1.IngressTLS{
				{
					Hosts:      []string{HostName},
					SecretName: SecretName,
				},
			},
		},
	}

	s.False(isIngressNeedsUpdate(iCur, iOld), "removing the annotation 'vice-president/replace-cert: \"true\"' should be ignored")

	iOld.Annotations = map[string]string{}
	iCur.Annotations = map[string]string{"vice-president/replace-cert": "true"}
	s.True(isIngressNeedsUpdate(iCur, iOld), "adding the annotation 'vice-president/replace-cert: \"true\"' should trigger an update")
	//reset
	iOld.Annotations = map[string]string{"vice-president": "true", "vice-president/replace-cert": "true"}
	iCur.Annotations = map[string]string{"vice-president/replace-cert": "true"}

	iCur.Annotations = map[string]string{}
	s.True(isIngressNeedsUpdate(iCur, iOld), "removing the annotation 'vice-president: \"true\"' should be trigger an update")
	//reset
	iCur.Annotations = map[string]string{"vice-president": "true"}

	iCur.Spec = extensionsv1beta1.IngressSpec{
		TLS: []extensionsv1beta1.IngressTLS{
			{
				Hosts:      []string{"foobar.com"},
				SecretName: SecretName,
			},
		},
	}
	s.True(isIngressNeedsUpdate(iCur, iOld), "changing the ingress.spec should trigger an update")
}
