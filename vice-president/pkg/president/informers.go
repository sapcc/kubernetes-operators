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
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	corev1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	corev1Informers "k8s.io/client-go/informers/core/v1"
	v1beta1Informers "k8s.io/client-go/informers/extensions/v1beta1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

func newIngressInformer(clientset *kubernetes.Clientset, options Options, queue workqueue.RateLimitingInterface, logger log.Logger) cache.SharedIndexInformer {
	logger = log.NewLoggerWith(logger, "component", "ingress informer")

	ingressInformer := v1beta1Informers.NewIngressInformer(
		clientset,
		options.Namespace,
		options.ResyncInterval,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: func(obj interface{}) {
			i := obj.(*extensionsv1beta1.Ingress)
			key, err := cache.MetaNamespaceKeyFunc(obj)
			if err != nil {
				logger.LogError("couldn't add ingress", err, "key", i)
				return
			}
			queue.AddRateLimited(key)
		},
		UpdateFunc: func(oldObj, newObj interface{}) {
			iOld := oldObj.(*extensionsv1beta1.Ingress)
			iNew := newObj.(*extensionsv1beta1.Ingress)

			if !isIngressNeedsUpdate(iNew, iOld) {
				logger.LogDebug("nothing changed. no need to update ingress", "key", keyFunc(iOld))
				return
			}

			key, err := cache.MetaNamespaceKeyFunc(iNew)
			if err != nil {
				logger.LogError("couldn't add ingress %s/%s", err, "key", keyFunc(iNew))
				return
			}
			logger.LogDebug("ingress was updated", "key", key)
			queue.AddRateLimited(key)
		},
	})

	return ingressInformer
}

func newSecretInformer(clientset *kubernetes.Clientset, options Options, queue workqueue.RateLimitingInterface, logger log.Logger) cache.SharedIndexInformer {
	logger = log.NewLoggerWith(logger, "component", "secret informer")

	secretInformer := corev1Informers.NewSecretInformer(
		clientset,
		options.Namespace,
		options.ResyncInterval,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	secretInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		DeleteFunc: func(obj interface{}) {
			secret := obj.(*corev1.Secret)
			// If secret is deleted but used by an ingress, requeue the ingress.
			if ingressKey, ok := secret.GetAnnotations()[AnnotationSecretClaimedByIngress]; ok {
				logger.LogDebug("secret was deleted. re-queueing ingress", "secret", keyFunc(secret), "ingress", keyFunc(ingressKey))
				queue.AddAfter(ingressKey, BaseDelay)
			}
		},
	})

	return secretInformer
}
