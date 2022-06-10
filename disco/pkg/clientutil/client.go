package clientutil

import (
	"context"
	"fmt"

	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/api/equality"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

const debugLogLevel = 1

// OperationResult is the action result of a CreateOrUpdate call
type OperationResult string

const ( // They should complete the sentence "Deployment default/foo has been ..."
	// OperationResultNone means that the resource has not been changed
	OperationResultNone OperationResult = "unchanged"
	// OperationResultCreated means that a new resource is created
	OperationResultCreated OperationResult = "created"
	// OperationResultUpdated means that an existing resource is updated
	OperationResultUpdated OperationResult = "updated"
)

func CreateOrPatch(ctx context.Context, c client.Client, obj client.Object, mutate func() error) (OperationResult, error) {
	if err := c.Get(ctx, client.ObjectKeyFromObject(obj), obj); err != nil {
		if !apierrors.IsNotFound(err) {
			return OperationResultNone, err
		}
		if err := mutate(); err != nil {
			return OperationResultNone, errors.Wrap(err, "mutating object failed")
		}
		if err := c.Create(ctx, obj); err != nil {
			return OperationResultNone, IgnoreAlreadyExists(err)
		}
		return OperationResultCreated, nil
	}
	if o, err := meta.Accessor(obj); err == nil {
		if o.GetDeletionTimestamp() != nil {
			return OperationResultNone, fmt.Errorf("the resource %s/%s already exists but is marked for deletion", o.GetNamespace(), o.GetName())
		}
	}

	return patch(ctx, c, obj, mutate, false)
}

func Patch(ctx context.Context, c client.Client, obj client.Object, mutate func() error) (OperationResult, error) {
	return patch(ctx, c, obj, mutate, false)
}

func PatchStatus(ctx context.Context, c client.Client, obj client.Object, mutate func() error) (OperationResult, error) {
	return patch(ctx, c, obj, mutate, true)
}

func patch(ctx context.Context, c client.Client, obj client.Object, mutate func() error, status bool) (OperationResult, error) {
	before := obj.DeepCopyObject().(client.Object)
	if err := mutate(); err != nil {
		return OperationResultNone, errors.Wrap(err, "mutating object failed")
	}
	if equality.Semantic.DeepEqual(before, obj) {
		return OperationResultNone, nil
	}
	patch := client.MergeFrom(before)

	var err error
	if status {
		err = c.Status().Patch(ctx, obj, patch)
	} else {
		err = c.Patch(ctx, obj, patch)
	}
	if err != nil {
		return OperationResultNone, err
	}

	return OperationResultUpdated, nil
}
