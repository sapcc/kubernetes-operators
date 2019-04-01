package president

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
)

func (s *TestSuite) TestIsLastHostInIngressSpec() {
	LastHost := "lastHost.com"

	ingress := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      IngressName,
			Annotations: map[string]string{
				"vice-president": "true",
			},
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
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
	testData := map[*v1beta1.Ingress]bool{
		{
			ObjectMeta: metav1.ObjectMeta{
				Namespace: Namespace,
				Name:      IngressName,
				Annotations: map[string]string{
					"vice-president":              "true",
					"vice-president/replace-cert": "true",
				},
			},
			Spec: v1beta1.IngressSpec{
				TLS: []v1beta1.IngressTLS{
					{
						Hosts:      []string{HostName},
						SecretName: SecretName,
					},
				},
			},
		}: true,
		{
			ObjectMeta: metav1.ObjectMeta{
				Namespace: Namespace,
				Name:      IngressName,
				Annotations: map[string]string{
					"vice-president": "true",
				},
			},
			Spec: v1beta1.IngressSpec{
				TLS: []v1beta1.IngressTLS{
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
	testData := map[*v1beta1.Ingress]bool{
		{
			ObjectMeta: metav1.ObjectMeta{
				Namespace: Namespace,
				Name:      "DoNotIgnoreMe!",
				Annotations: map[string]string{
					"vice-president": "true",
				},
			},
		}: true,
		{
			ObjectMeta: metav1.ObjectMeta{
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
	iOld := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      "DoNotIgnoreMe!",
			Annotations: map[string]string{
				"vice-president":              "true",
				"vice-president/replace-cert": "true",
			},
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
				{
					Hosts:      []string{HostName},
					SecretName: SecretName,
				},
			},
		},
	}

	iCur := &v1beta1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: Namespace,
			Name:      "DoNotIgnoreMe!",
			Annotations: map[string]string{
				"vice-president": "true",
			},
		},
		Spec: v1beta1.IngressSpec{
			TLS: []v1beta1.IngressTLS{
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

	iCur.Spec = v1beta1.IngressSpec{
		TLS: []v1beta1.IngressTLS{
			{
				Hosts:      []string{"foobar.com"},
				SecretName: SecretName,
			},
		},
	}
	s.True(isIngressNeedsUpdate(iCur, iOld), "changing the ingress.spec should trigger an update")
}
