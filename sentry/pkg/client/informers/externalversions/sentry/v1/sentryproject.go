/*
Copyright The Kubernetes Authors.

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

// Code generated by informer-gen. DO NOT EDIT.

package v1

import (
	"context"
	time "time"

	sentryv1 "github.com/sapcc/kubernetes-operators/sentry/pkg/apis/sentry/v1"
	versioned "github.com/sapcc/kubernetes-operators/sentry/pkg/client/clientset/versioned"
	internalinterfaces "github.com/sapcc/kubernetes-operators/sentry/pkg/client/informers/externalversions/internalinterfaces"
	v1 "github.com/sapcc/kubernetes-operators/sentry/pkg/client/listers/sentry/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	runtime "k8s.io/apimachinery/pkg/runtime"
	watch "k8s.io/apimachinery/pkg/watch"
	cache "k8s.io/client-go/tools/cache"
)

// SentryProjectInformer provides access to a shared informer and lister for
// SentryProjects.
type SentryProjectInformer interface {
	Informer() cache.SharedIndexInformer
	Lister() v1.SentryProjectLister
}

type sentryProjectInformer struct {
	factory          internalinterfaces.SharedInformerFactory
	tweakListOptions internalinterfaces.TweakListOptionsFunc
	namespace        string
}

// NewSentryProjectInformer constructs a new informer for SentryProject type.
// Always prefer using an informer factory to get a shared informer instead of getting an independent
// one. This reduces memory footprint and number of connections to the server.
func NewSentryProjectInformer(client versioned.Interface, namespace string, resyncPeriod time.Duration, indexers cache.Indexers) cache.SharedIndexInformer {
	return NewFilteredSentryProjectInformer(client, namespace, resyncPeriod, indexers, nil)
}

// NewFilteredSentryProjectInformer constructs a new informer for SentryProject type.
// Always prefer using an informer factory to get a shared informer instead of getting an independent
// one. This reduces memory footprint and number of connections to the server.
func NewFilteredSentryProjectInformer(client versioned.Interface, namespace string, resyncPeriod time.Duration, indexers cache.Indexers, tweakListOptions internalinterfaces.TweakListOptionsFunc) cache.SharedIndexInformer {
	return cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options metav1.ListOptions) (runtime.Object, error) {
				if tweakListOptions != nil {
					tweakListOptions(&options)
				}
				return client.SentryV1().SentryProjects(namespace).List(context.TODO(), options)
			},
			WatchFunc: func(options metav1.ListOptions) (watch.Interface, error) {
				if tweakListOptions != nil {
					tweakListOptions(&options)
				}
				return client.SentryV1().SentryProjects(namespace).Watch(context.TODO(), options)
			},
		},
		&sentryv1.SentryProject{},
		resyncPeriod,
		indexers,
	)
}

func (f *sentryProjectInformer) defaultInformer(client versioned.Interface, resyncPeriod time.Duration) cache.SharedIndexInformer {
	return NewFilteredSentryProjectInformer(client, f.namespace, resyncPeriod, cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc}, f.tweakListOptions)
}

func (f *sentryProjectInformer) Informer() cache.SharedIndexInformer {
	return f.factory.InformerFor(&sentryv1.SentryProject{}, f.defaultInformer)
}

func (f *sentryProjectInformer) Lister() v1.SentryProjectLister {
	return v1.NewSentryProjectLister(f.Informer().GetIndexer())
}
