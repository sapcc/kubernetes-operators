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

package fake

import (
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	labels "k8s.io/apimachinery/pkg/labels"
	schema "k8s.io/apimachinery/pkg/runtime/schema"
	types "k8s.io/apimachinery/pkg/types"
	watch "k8s.io/apimachinery/pkg/watch"
	testing "k8s.io/client-go/testing"
	storage "k8s.io/kubernetes/pkg/apis/storage"
)

// FakeStorageClasses implements StorageClassInterface
type FakeStorageClasses struct {
	Fake *FakeStorage
}

var storageclassesResource = schema.GroupVersionResource{Group: "storage.k8s.io", Version: "", Resource: "storageclasses"}

var storageclassesKind = schema.GroupVersionKind{Group: "storage.k8s.io", Version: "", Kind: "StorageClass"}

func (c *FakeStorageClasses) Create(storageClass *storage.StorageClass) (result *storage.StorageClass, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewRootCreateAction(storageclassesResource, storageClass), &storage.StorageClass{})
	if obj == nil {
		return nil, err
	}
	return obj.(*storage.StorageClass), err
}

func (c *FakeStorageClasses) Update(storageClass *storage.StorageClass) (result *storage.StorageClass, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewRootUpdateAction(storageclassesResource, storageClass), &storage.StorageClass{})
	if obj == nil {
		return nil, err
	}
	return obj.(*storage.StorageClass), err
}

func (c *FakeStorageClasses) Delete(name string, options *v1.DeleteOptions) error {
	_, err := c.Fake.
		Invokes(testing.NewRootDeleteAction(storageclassesResource, name), &storage.StorageClass{})
	return err
}

func (c *FakeStorageClasses) DeleteCollection(options *v1.DeleteOptions, listOptions v1.ListOptions) error {
	action := testing.NewRootDeleteCollectionAction(storageclassesResource, listOptions)

	_, err := c.Fake.Invokes(action, &storage.StorageClassList{})
	return err
}

func (c *FakeStorageClasses) Get(name string, options v1.GetOptions) (result *storage.StorageClass, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewRootGetAction(storageclassesResource, name), &storage.StorageClass{})
	if obj == nil {
		return nil, err
	}
	return obj.(*storage.StorageClass), err
}

func (c *FakeStorageClasses) List(opts v1.ListOptions) (result *storage.StorageClassList, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewRootListAction(storageclassesResource, storageclassesKind, opts), &storage.StorageClassList{})
	if obj == nil {
		return nil, err
	}

	label, _, _ := testing.ExtractFromListOptions(opts)
	if label == nil {
		label = labels.Everything()
	}
	list := &storage.StorageClassList{}
	for _, item := range obj.(*storage.StorageClassList).Items {
		if label.Matches(labels.Set(item.Labels)) {
			list.Items = append(list.Items, item)
		}
	}
	return list, err
}

// Watch returns a watch.Interface that watches the requested storageClasses.
func (c *FakeStorageClasses) Watch(opts v1.ListOptions) (watch.Interface, error) {
	return c.Fake.
		InvokesWatch(testing.NewRootWatchAction(storageclassesResource, opts))
}

// Patch applies the patch and returns the patched storageClass.
func (c *FakeStorageClasses) Patch(name string, pt types.PatchType, data []byte, subresources ...string) (result *storage.StorageClass, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewRootPatchSubresourceAction(storageclassesResource, name, data, subresources...), &storage.StorageClass{})
	if obj == nil {
		return nil, err
	}
	return obj.(*storage.StorageClass), err
}
