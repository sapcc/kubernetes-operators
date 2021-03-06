/*
Copyright 2018 The Kubernetes Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1

import (
	serializer "k8s.io/apimachinery/pkg/runtime/serializer"
	rest "k8s.io/client-go/rest"
	"k8s.io/kubernetes/federation/client/clientset_generated/federation_clientset/scheme"
	v1 "k8s.io/kubernetes/pkg/api/v1"
)

type CoreV1Interface interface {
	RESTClient() rest.Interface
	ConfigMapsGetter
	EventsGetter
	NamespacesGetter
	SecretsGetter
	ServicesGetter
}

// CoreV1Client is used to interact with features provided by the  group.
type CoreV1Client struct {
	restClient rest.Interface
}

func (c *CoreV1Client) ConfigMaps(namespace string) ConfigMapInterface {
	return newConfigMaps(c, namespace)
}

func (c *CoreV1Client) Events(namespace string) EventInterface {
	return newEvents(c, namespace)
}

func (c *CoreV1Client) Namespaces() NamespaceInterface {
	return newNamespaces(c)
}

func (c *CoreV1Client) Secrets(namespace string) SecretInterface {
	return newSecrets(c, namespace)
}

func (c *CoreV1Client) Services(namespace string) ServiceInterface {
	return newServices(c, namespace)
}

// NewForConfig creates a new CoreV1Client for the given config.
func NewForConfig(c *rest.Config) (*CoreV1Client, error) {
	config := *c
	if err := setConfigDefaults(&config); err != nil {
		return nil, err
	}
	client, err := rest.RESTClientFor(&config)
	if err != nil {
		return nil, err
	}
	return &CoreV1Client{client}, nil
}

// NewForConfigOrDie creates a new CoreV1Client for the given config and
// panics if there is an error in the config.
func NewForConfigOrDie(c *rest.Config) *CoreV1Client {
	client, err := NewForConfig(c)
	if err != nil {
		panic(err)
	}
	return client
}

// New creates a new CoreV1Client for the given RESTClient.
func New(c rest.Interface) *CoreV1Client {
	return &CoreV1Client{c}
}

func setConfigDefaults(config *rest.Config) error {
	gv := v1.SchemeGroupVersion
	config.GroupVersion = &gv
	config.APIPath = "/api"
	config.NegotiatedSerializer = serializer.DirectCodecFactory{CodecFactory: scheme.Codecs}

	if config.UserAgent == "" {
		config.UserAgent = rest.DefaultKubernetesUserAgent()
	}

	return nil
}

// RESTClient returns a RESTClient that is used to communicate
// with API server by this client implementation.
func (c *CoreV1Client) RESTClient() rest.Interface {
	if c == nil {
		return nil
	}
	return c.restClient
}
