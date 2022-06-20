package clientutil

import apierrors "k8s.io/apimachinery/pkg/api/errors"

// IgnoreAlreadyExists returns nil on IsAlreadyExists errors.
func IgnoreAlreadyExists(err error) error {
	if apierrors.IsAlreadyExists(err) {
		return nil
	}
	return err
}
