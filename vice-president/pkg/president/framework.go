package president

import (
	"context"
	"fmt"

	"github.com/pkg/errors"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	corev1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	metaV1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	apimachineryWatch "k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/watch"
)

type k8sFramework struct {
	*kubernetes.Clientset
	logger log.Logger
}

func newK8sFramework(config *rest.Config, logger log.Logger) (*k8sFramework, error) {
	clientset, err := kubernetes.NewForConfig(config)
	return &k8sFramework{
		clientset,
		log.NewLoggerWith(logger, "component", "k8sFramework"),
	}, err
}

// getOrCreateSecret returns an existing Secret or creates it if not found and waits until the operation times out or is completed.
func (k8s *k8sFramework) getOrCreateSecret(namespace, name string, labels, annotations map[string]string) (*corev1.Secret, error) {
	secret, err := k8s.CoreV1().Secrets(namespace).Get(name, metaV1.GetOptions{})
	if err != nil {
		// Create secret if not found.
		if apiErrors.IsNotFound(err) {
			k8s.logger.LogInfo("creating secret", "key", fmt.Sprintf("%s/%s", namespace, name))
			secret = newEmptySecret(namespace, name, labels, annotations)
			if err := k8s.createSecret(secret); err != nil {
				return nil, err
			}
			return k8s.CoreV1().Secrets(namespace).Get(name, metaV1.GetOptions{})
		}
		// Return any other error.
		return secret, errors.Wrapf(err, "secret %s/%s exists but failed to get it", namespace, name)
	}
	return secret, err
}

// createSecret create the given Secret and waits until the operation times out or is completed.
func (k8s *k8sFramework) createSecret(secret *corev1.Secret) error {
	newSecret, err := k8s.CoreV1().Secrets(secret.GetNamespace()).Create(secret)
	if err != nil {
		return err
	}

	k8s.logger.LogDebug("added upstream secret", "secret", keyFunc(secret))

	return k8s.waitForUpstreamSecret(newSecret, isSecretAddedOrModified)
}

// updateSecret updates an existing Secret and waits until the operation times out or is completed.
func (k8s *k8sFramework) updateSecret(oldSecret, newSecret *corev1.Secret, conditionFuncs ...watch.ConditionFunc) error {
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

// deleteSecret deletes an existing secret and waits until the operation times out or is completed.
func (k8s *k8sFramework) deleteSecret(secret *corev1.Secret) error {
	if err := k8s.CoreV1().Secrets(secret.GetNamespace()).Delete(secret.GetName(), &metaV1.DeleteOptions{}); err != nil {
		return err
	}

	k8s.logger.LogDebug("deleting secret", "secret", keyFunc(secret))

	return k8s.waitForUpstreamSecret(secret, isSecretDeleted)
}

func (k8s *k8sFramework) removeSecretAnnotation(secret *corev1.Secret, annotation string) error {
	secret, err := k8s.Clientset.CoreV1().Secrets(secret.GetNamespace()).Get(secret.GetName(), metaV1.GetOptions{})
	if err != nil {
		return err
	}

	newSecret := secret.DeepCopy()
	annotations := newSecret.GetAnnotations()
	delete(annotations, annotation)
	newSecret.Annotations = annotations

	return k8s.updateSecret(
		secret, newSecret,
		func(event apimachineryWatch.Event) (bool, error) {
			switch event.Type {
			case apimachineryWatch.Deleted:
				return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "secret"}, "")
			}
			switch secret := event.Object.(type) {
			case *corev1.Secret:
				return !isSecretHasAnnotation(secret, annotation), nil
			}
			return false, nil
		},
	)
}

// waitForUpstreamSecret watches the given secret and wait for max. t minutes until the given condition applies.
func (k8s *k8sFramework) waitForUpstreamSecret(secret *corev1.Secret, conditionFuncs ...watch.ConditionFunc) error {
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

// getIngress returns the ingress or an error.
func (k8s *k8sFramework) getIngress(namespace, name string) (*extensionsv1beta1.Ingress, error) {
	return k8s.ExtensionsV1beta1().Ingresses(namespace).Get(name, metaV1.GetOptions{})
}

// updateIngress updates an existing Ingress and waits until the operation times out or is completed.
func (k8s *k8sFramework) updateIngress(oldIngress, newIngress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
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

// removeIngressAnnotation removes the given annotation from an ingress and waits until operation times out or is completed.
func (k8s *k8sFramework) removeIngressAnnotation(ingress *extensionsv1beta1.Ingress, annotation string) error {
	ingress, err := k8s.getIngress(ingress.GetNamespace(), ingress.GetName())
	if err != nil {
		return err
	}

	newIngress := ingress.DeepCopy()
	annotations := newIngress.GetAnnotations()
	delete(annotations, annotation)
	newIngress.Annotations = annotations

	k8s.logger.LogDebug("removing annotation from ingress", "ingress", keyFunc(ingress), "annotation", annotation)

	return k8s.updateIngress(
		ingress, newIngress,
		func(event apimachineryWatch.Event) (bool, error) {
			switch event.Type {
			case apimachineryWatch.Deleted:
				return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
			}
			switch ing := event.Object.(type) {
			case *extensionsv1beta1.Ingress:
				return !isIngressHasAnnotation(ing, annotation), nil
			}
			return false, nil
		},
	)
}

// waitForUpstreamIngress watches the given Ingress and wait for max. t minutes until the given condition applies.
func (k8s *k8sFramework) waitForUpstreamIngress(ingress *extensionsv1beta1.Ingress, conditionFuncs ...watch.ConditionFunc) error {
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

// ensureVicePresidentFinalizerExists ensures the Finalizer exists on the given Ingress or returns an error.
func (k8s *k8sFramework) ensureVicePresidentFinalizerExists(ingress *extensionsv1beta1.Ingress) error {
	// Add finalizer if not present and ingress was not deleted.
	if !ingressHasVicePresidentFinalizer(ingress) && !ingressHasDeletionTimestamp(ingress) {
		newIngress := ingress.DeepCopy()
		newIngress.Finalizers = append(newIngress.GetFinalizers(), FinalizerVicePresident)

		k8s.logger.LogDebug("adding finalizer to ingress", "ingress", keyFunc(ingress), "finalizer", FinalizerVicePresident)

		return k8s.updateIngress(
			ingress, newIngress,
			func(event apimachineryWatch.Event) (bool, error) {
				switch event.Type {
				case apimachineryWatch.Deleted:
					return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
				}
				switch ing := event.Object.(type) {
				case *extensionsv1beta1.Ingress:
					return ingressHasVicePresidentFinalizer(ing), nil
				}
				return false, nil
			},
		)
	}
	return nil
}

// ensureVicePresidentFinalizerRemoved ensures the Finalizer was removed from the given Ingress or returns an error.
func (k8s *k8sFramework) ensureVicePresidentFinalizerRemoved(ingress *extensionsv1beta1.Ingress) error {
	// Do not remove finalizer if DeletionTimestamp is not set.
	if ingressHasVicePresidentFinalizer(ingress) && ingressHasDeletionTimestamp(ingress) {
		newIngress := ingress.DeepCopy()
		for i, fin := range newIngress.GetFinalizers() {
			if fin == FinalizerVicePresident {
				// Delete but preserve order.
				newIngress.Finalizers = append(newIngress.Finalizers[:i], newIngress.Finalizers[i+1:]...)

				k8s.logger.LogDebug("removing finalizer from ingress", "ingress", keyFunc(ingress), "finalizer", FinalizerVicePresident)

				return k8s.updateIngress(
					ingress, newIngress,
					func(event apimachineryWatch.Event) (bool, error) {
						switch event.Type {
						case apimachineryWatch.Deleted:
							return false, apiErrors.NewNotFound(schema.GroupResource{Resource: "ingress"}, "")
						}
						switch ing := event.Object.(type) {
						case *extensionsv1beta1.Ingress:
							return !ingressHasVicePresidentFinalizer(ing), nil
						}
						return false, nil
					},
				)
			}
		}
	}
	return nil
}
