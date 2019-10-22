package k8sutils

import (
	"context"
	"fmt"
	"time"

	"github.com/pkg/errors"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/config"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	corev1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	apimetav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachineryWatch "k8s.io/apimachinery/pkg/watch"
	corev1Informers "k8s.io/client-go/informers/core/v1"
	v1beta1Informers "k8s.io/client-go/informers/extensions/v1beta1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	v12 "k8s.io/client-go/kubernetes/typed/core/v1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/tools/watch"
)

// WaitTimeout is the time we're waiting before considering an operation failed.
const WaitTimeout = 2 * time.Minute

// K8sFramework ...
type K8sFramework struct {
	*kubernetes.Clientset
	logger          log.Logger
	finalizer       string
	eventRecorder   record.EventRecorder
	ingressInformer cache.SharedIndexInformer
	secretInformer  cache.SharedIndexInformer
}

// NewK8sFramework returns a new k8s framework.
func NewK8sFramework(opts config.Options, logger log.Logger) (*K8sFramework, error) {
	logger = log.NewLoggerWith(logger, "component", "K8sFramework")

	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}
	if opts.KubeConfig != "" {
		rules.ExplicitPath = opts.KubeConfig
	}

	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		return nil, err
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	ingressInformer := v1beta1Informers.NewIngressInformer(
		clientset,
		opts.Namespace,
		opts.ResyncInterval,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	secretInformer := corev1Informers.NewSecretInformer(
		clientset,
		opts.Namespace,
		opts.ResyncInterval,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	b := record.NewBroadcaster()
	b.StartLogging(logger.LogEvent)
	b.StartRecordingToSink(&v12.EventSinkImpl{
		Interface: clientset.CoreV1().Events(apimetav1.NamespaceAll),
	})
	eventRecorder := b.NewRecorder(scheme.Scheme, corev1.EventSource{
		Component: opts.EventComponent,
	})

	return &K8sFramework{
		Clientset:       clientset,
		logger:          logger,
		finalizer:       opts.Finalizer,
		eventRecorder:   eventRecorder,
		ingressInformer: ingressInformer,
		secretInformer:  secretInformer,
	}, nil
}

// Run starts the informers.
func (k8s *K8sFramework) Run(stopCh <-chan struct{}) {
	go k8s.ingressInformer.Run(stopCh)
	go k8s.secretInformer.Run(stopCh)
}

// WaitForCacheSync returns true if all informer caches have been synced.
func (k8s *K8sFramework) WaitForCacheSync(stopCh <-chan struct{}) bool {
	return cache.WaitForCacheSync(
		stopCh,
		k8s.ingressInformer.HasSynced,
		k8s.secretInformer.HasSynced,
	)
}

// AddIngressInformerEventHandler adds event handlers to the ingress informer.
func (k8s *K8sFramework) AddIngressInformerEventHandler(addFunc, deleteFunc func(obj interface{}), updateFunc func(oldObj, newObj interface{})) {
	k8s.ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    addFunc,
		UpdateFunc: updateFunc,
		DeleteFunc: deleteFunc,
	})
}

// AddSecretInformerEventHandler adds event handlers to the secret informer.
func (k8s *K8sFramework) AddSecretInformerEventHandler(addFunc, deleteFunc func(obj interface{}), updateFunc func(oldObj, newObj interface{})) {
	k8s.secretInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    addFunc,
		UpdateFunc: updateFunc,
		DeleteFunc: deleteFunc,
	})
}

// Eventf emits an event via the event recorder.
func (k8s *K8sFramework) Eventf(object runtime.Object, eventType, reason, messageFmt string, args ...interface{}) {
	k8s.eventRecorder.Eventf(object, eventType, reason, messageFmt, args)
}

// GetIngressFromIndexerByKey gets an ingress from the ingress informer indexer by key.
func (k8s *K8sFramework) GetIngressFromIndexerByKey(key string) (interface{}, bool, error) {
	return k8s.ingressInformer.GetIndexer().GetByKey(key)
}

// GetIngressInformerStore returns a the store of the ingress informer.
func (k8s *K8sFramework) GetIngressInformerStore() cache.Store {
	return k8s.ingressInformer.GetStore()
}

// GetOrCreateSecret returns an existing Secret or creates it if not found and waits until the operation times out or is completed.
func (k8s *K8sFramework) GetOrCreateSecret(namespace, name string, labels, annotations map[string]string) (*corev1.Secret, error) {
	secret, err := k8s.CoreV1().Secrets(namespace).Get(name, metaV1.GetOptions{})
	if err != nil {
		// Create secret if not found.
		if apiErrors.IsNotFound(err) {
			k8s.logger.LogInfo("creating secret", "key", fmt.Sprintf("%s/%s", namespace, name))
			secret = newEmptySecret(namespace, name, labels, annotations)
			if err := k8s.CreateSecret(secret); err != nil {
				return nil, err
			}
			return k8s.CoreV1().Secrets(namespace).Get(name, metaV1.GetOptions{})
		}
		// Return any other error.
		return secret, errors.Wrapf(err, "secret %s/%s exists but failed to get it", namespace, name)
	}
	return secret, err
}

// CreateSecret create the given Secret and waits until the operation times out or is completed.
func (k8s *K8sFramework) CreateSecret(secret *corev1.Secret) error {
	newSecret, err := k8s.CoreV1().Secrets(secret.GetNamespace()).Create(secret)
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("added upstream secret", "secret", keyFunc(secret))

	return k8s.waitForUpstreamSecret(newSecret, isSecretAddedOrModified)
}

// UpdateSecret updates an existing Secret and waits until the operation times out or is completed.
func (k8s *K8sFramework) UpdateSecret(oldSecret, newSecret *corev1.Secret, conditionFuncs ...watch.ConditionFunc) error {
	oldSecret, err := k8s.CoreV1().Secrets(oldSecret.GetNamespace()).Get(oldSecret.GetName(), metaV1.GetOptions{})
	if err != nil {
		return err
	}

	// Nothing to update.
	if !isSecretNeedsUpdate(oldSecret, newSecret) {
		return nil
	}

	updatedSecret, err := k8s.CoreV1().Secrets(oldSecret.GetNamespace()).Update(newSecret)
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("updating secret", "secret", keyFunc(updatedSecret))

	if conditionFuncs == nil {
		conditionFuncs = []watch.ConditionFunc{isSecretAddedOrModified}
	}

	return k8s.waitForUpstreamSecret(updatedSecret, conditionFuncs...)
}

// DeleteSecret deletes an existing secret and waits until the operation times out or is completed.
func (k8s *K8sFramework) DeleteSecret(secret *corev1.Secret) error {
	if err := k8s.CoreV1().Secrets(secret.GetNamespace()).Delete(secret.GetName(), &metaV1.DeleteOptions{}); err != nil {
		return err
	}

	k8s.logger.LogDebug("deleting secret", "secret", keyFunc(secret))

	return k8s.waitForUpstreamSecret(secret, isSecretDeleted)
}

// RemoveSecretAnnotation removes an annotation from the given secret.
func (k8s *K8sFramework) RemoveSecretAnnotation(secret *corev1.Secret, annotation string) error {
	secret, err := k8s.Clientset.CoreV1().Secrets(secret.GetNamespace()).Get(secret.GetName(), metaV1.GetOptions{})
	if err != nil {
		return err
	}

	newSecret := secret.DeepCopy()
	annotations := newSecret.GetAnnotations()
	delete(annotations, annotation)
	newSecret.Annotations = annotations

	return k8s.UpdateSecret(
		secret, newSecret,
		func(event apimachineryWatch.Event) (bool, error) {
			switch event.Type {
			case apimachineryWatch.Deleted:
				return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "secret"}, secret.GetName())
			}
			switch secret := event.Object.(type) {
			case *corev1.Secret:
				return !secretHasAnnotation(secret, annotation), nil
			}
			return false, nil
		},
	)
}

// GetIngress returns the ingress or an error.
func (k8s *K8sFramework) GetIngress(namespace, name string) (*extensionsv1beta1.Ingress, error) {
	return k8s.ExtensionsV1beta1().Ingresses(namespace).Get(name, metaV1.GetOptions{})
}

// UpdateIngress updates an existing Ingress and waits until the operation times out or is completed.
func (k8s *K8sFramework) UpdateIngress(oldIngress, newIngress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
	oldIngress, err := k8s.ExtensionsV1beta1().Ingresses(oldIngress.GetNamespace()).Get(oldIngress.GetName(), metaV1.GetOptions{})
	if err != nil {
		return err
	}

	// Nothing to update.
	if !isIngressNeedsUpdate(oldIngress, newIngress) {
		return nil
	}

	updatedIngress, err := k8s.ExtensionsV1beta1().Ingresses(oldIngress.GetNamespace()).Update(newIngress)
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("updating ingress", "ingress", keyFunc(updatedIngress))

	if conditionFuncs == nil {
		conditionFuncs = []watch.ConditionFunc{isIngressAddedOrModified}
	}

	return k8s.waitForUpstreamIngress(updatedIngress, conditionFuncs...)
}

// RemoveIngressAnnotation removes the given annotation from an ingress and waits until operation times out or is completed.
func (k8s *K8sFramework) RemoveIngressAnnotation(ingress *extensionsv1beta1.Ingress, annotation string) error {
	ingress, err := k8s.GetIngress(ingress.GetNamespace(), ingress.GetName())
	if err != nil {
		return err
	}

	newIngress := ingress.DeepCopy()
	annotations := newIngress.GetAnnotations()
	delete(annotations, annotation)
	newIngress.Annotations = annotations

	k8s.logger.LogDebug("removing annotation from ingress", "ingress", keyFunc(ingress), "annotation", annotation)

	return k8s.UpdateIngress(
		ingress, newIngress,
		func(event apimachineryWatch.Event) (bool, error) {
			switch event.Type {
			case apimachineryWatch.Deleted:
				return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
			}
			switch ing := event.Object.(type) {
			case *extensionsv1beta1.Ingress:
				return !IngressHasAnnotation(ing, annotation), nil
			}
			return false, nil
		},
	)
}

// EnsureVicePresidentFinalizerExists ensures the Finalizer exists on the given Ingress or returns an error.
func (k8s *K8sFramework) EnsureVicePresidentFinalizerExists(ingress *extensionsv1beta1.Ingress) error {
	// Add finalizer if not present and ingress was not deleted.
	if !IngressHasFinalizer(ingress, k8s.finalizer) && !IngressHasDeletionTimestamp(ingress) {
		newIngress := ingress.DeepCopy()
		newIngress.Finalizers = append(newIngress.GetFinalizers(), k8s.finalizer)

		k8s.logger.LogDebug("adding finalizer to ingress", "ingress", keyFunc(ingress), "finalizer", k8s.finalizer)

		return k8s.UpdateIngress(
			ingress, newIngress,
			func(event apimachineryWatch.Event) (bool, error) {
				switch event.Type {
				case apimachineryWatch.Deleted:
					return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
				}
				switch ing := event.Object.(type) {
				case *extensionsv1beta1.Ingress:
					return IngressHasFinalizer(ing, k8s.finalizer), nil
				}
				return false, nil
			},
		)
	}
	return nil
}

// EnsureVicePresidentFinalizerRemoved ensures the Finalizer was removed from the given Ingress or returns an error.
func (k8s *K8sFramework) EnsureVicePresidentFinalizerRemoved(ingress *extensionsv1beta1.Ingress) error {
	// Do not remove finalizer if DeletionTimestamp is not set.
	if IngressHasFinalizer(ingress, k8s.finalizer) && IngressHasDeletionTimestamp(ingress) {
		newIngress := ingress.DeepCopy()
		for i, fin := range newIngress.GetFinalizers() {
			if fin == k8s.finalizer {
				// Delete but preserve order.
				newIngress.Finalizers = append(newIngress.Finalizers[:i], newIngress.Finalizers[i+1:]...)

				k8s.logger.LogDebug("removing finalizer from ingress", "ingress", keyFunc(ingress), "finalizer", k8s.finalizer)

				return k8s.UpdateIngress(
					ingress, newIngress,
					func(event apimachineryWatch.Event) (bool, error) {
						switch event.Type {
						case apimachineryWatch.Deleted:
							return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
						}
						switch ing := event.Object.(type) {
						case *extensionsv1beta1.Ingress:
							return !IngressHasFinalizer(ing, k8s.finalizer), nil
						}
						return false, nil
					},
				)
			}
		}
	}
	return nil
}

// waitForUpstreamSecret watches the given secret and wait for max. t minutes until the given condition applies.
func (k8s *K8sFramework) waitForUpstreamSecret(secret *corev1.Secret, conditionFuncs ...watch.ConditionFunc) error {
	ctx, _ := context.WithTimeout(context.TODO(), WaitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metaV1.ListOptions) (object runtime.Object, e error) {
				return k8s.CoreV1().Secrets(secret.GetNamespace()).List(metaV1.SingleObject(metaV1.ObjectMeta{Name: secret.GetName()}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.CoreV1().Secrets(secret.GetNamespace()).Watch(metaV1.SingleObject(metaV1.ObjectMeta{Name: secret.GetName()}))
			},
		},
		secret,
		nil,
		conditionFuncs...,
	)
	return err
}

// waitForUpstreamIngress watches the given Ingress and wait for max. t minutes until the given condition applies.
func (k8s *K8sFramework) waitForUpstreamIngress(ingress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
	ctx, _ := context.WithTimeout(context.TODO(), WaitTimeout)
	_, err := watch.UntilWithSync(
		ctx,
		&cache.ListWatch{
			ListFunc: func(options metaV1.ListOptions) (object runtime.Object, e error) {
				return k8s.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).List(metaV1.SingleObject(metaV1.ObjectMeta{Name: ingress.GetName()}))
			},
			WatchFunc: func(options metaV1.ListOptions) (i apimachineryWatch.Interface, e error) {
				return k8s.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).Watch(metaV1.SingleObject(metaV1.ObjectMeta{Name: ingress.GetName()}))
			},
		},
		ingress,
		nil,
		conditionFuncs...,
	)
	return err
}
