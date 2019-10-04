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

// Code generated by lister-gen. DO NOT EDIT.

package v1

import (
	v1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco.stable.sap.cc/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/tools/cache"
)

// DiscoRecordLister helps list DiscoRecords.
type DiscoRecordLister interface {
	// List lists all DiscoRecords in the indexer.
	List(selector labels.Selector) (ret []*v1.DiscoRecord, err error)
	// DiscoRecords returns an object that can list and get DiscoRecords.
	DiscoRecords(namespace string) DiscoRecordNamespaceLister
	DiscoRecordListerExpansion
}

// discoRecordLister implements the DiscoRecordLister interface.
type discoRecordLister struct {
	indexer cache.Indexer
}

// NewDiscoRecordLister returns a new DiscoRecordLister.
func NewDiscoRecordLister(indexer cache.Indexer) DiscoRecordLister {
	return &discoRecordLister{indexer: indexer}
}

// List lists all DiscoRecords in the indexer.
func (s *discoRecordLister) List(selector labels.Selector) (ret []*v1.DiscoRecord, err error) {
	err = cache.ListAll(s.indexer, selector, func(m interface{}) {
		ret = append(ret, m.(*v1.DiscoRecord))
	})
	return ret, err
}

// DiscoRecords returns an object that can list and get DiscoRecords.
func (s *discoRecordLister) DiscoRecords(namespace string) DiscoRecordNamespaceLister {
	return discoRecordNamespaceLister{indexer: s.indexer, namespace: namespace}
}

// DiscoRecordNamespaceLister helps list and get DiscoRecords.
type DiscoRecordNamespaceLister interface {
	// List lists all DiscoRecords in the indexer for a given namespace.
	List(selector labels.Selector) (ret []*v1.DiscoRecord, err error)
	// Get retrieves the DiscoRecord from the indexer for a given namespace and name.
	Get(name string) (*v1.DiscoRecord, error)
	DiscoRecordNamespaceListerExpansion
}

// discoRecordNamespaceLister implements the DiscoRecordNamespaceLister
// interface.
type discoRecordNamespaceLister struct {
	indexer   cache.Indexer
	namespace string
}

// List lists all DiscoRecords in the indexer for a given namespace.
func (s discoRecordNamespaceLister) List(selector labels.Selector) (ret []*v1.DiscoRecord, err error) {
	err = cache.ListAllByNamespace(s.indexer, s.namespace, selector, func(m interface{}) {
		ret = append(ret, m.(*v1.DiscoRecord))
	})
	return ret, err
}

// Get retrieves the DiscoRecord from the indexer for a given namespace and name.
func (s discoRecordNamespaceLister) Get(name string) (*v1.DiscoRecord, error) {
	obj, exists, err := s.indexer.GetByKey(s.namespace + "/" + name)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, errors.NewNotFound(v1.Resource("discorecord"), name)
	}
	return obj.(*v1.DiscoRecord), nil
}
