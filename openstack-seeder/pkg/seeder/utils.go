// Copyright 2017 SAP SE
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package seeder

import (
	"github.com/golang/glog"
	"reflect"
)

func MergeStructFields(dst, src interface{}) {
	in := reflect.ValueOf(src)
	out := reflect.ValueOf(dst)
	if src == nil || dst == nil {
		return
	}
	if in.Kind() == reflect.Ptr {
		in = in.Elem()
	}
	if out.Kind() == reflect.Ptr {
		out = out.Elem()
	}
	if in.Type() != out.Type() {
		// Explicit test prior to mergeStruct so that mistyped nils will fail
		glog.Error("type mismatch in ", in, ", out ", out)
		return
	}
	mergeStructFields(out, in)
}

func mergeStructFields(out, in reflect.Value) {
	for i := 0; i < in.NumField(); i++ {
		f := in.Type().Field(i)
		if isZero(in.Field(i)) {
			continue
		}
		switch f.Type.Kind() {
		case reflect.Bool, reflect.Float32, reflect.Float64, reflect.Int, reflect.Int32, reflect.Int64,
			reflect.String, reflect.Uint, reflect.Uint32, reflect.Uint64:
			if out.Field(i).CanSet() {
				glog.V(3).Info("merging field ", f.Name, ", new value ", in.Field(i))
				out.Field(i).Set(in.Field(i))
			}
		case reflect.Ptr:
			if f.Type.Elem().Kind() == reflect.Bool {
				glog.V(3).Info("merging field ", f.Name, ", new value ", in.Field(i))
				out.Field(i).Set(in.Field(i))
			}
		case reflect.Map:
			if out.Field(i).CanSet() {
				glog.V(3).Info("merging field ", f.Name, ", new value ", in.Field(i))
				merged := mergeMaps(out.Field(i).Interface().(map[string]string), in.Field(i).Interface().(map[string]string))
				out.Field(i).Set(reflect.ValueOf(merged))
			}
		case reflect.Slice:
			continue
		case reflect.Struct:
			continue
		default:
			glog.Error("unsupported type encountered in merge of ", f.Name, ": ", f.Type.Kind())
		}
	}
}

// overwriting duplicate keys, you should handle that if there is a need
func mergeMaps(maps ...map[string]string) map[string]string {
	result := make(map[string]string)
	for _, m := range maps {
		for k, v := range m {
			result[k] = v
		}
	}
	return result
}

func MergeStringSlices(slices ...[]string) []string {
	// merge slices
	set := make(map[string]bool)

	for _, s := range slices {
		for _, r := range s {
			set[r] = true
		}
	}

	result := make([]string, len(set))
	j := 0
	for r := range set {
		result[j] = r
		j++
	}
	return result
}

// isZero is mostly stolen from encoding/json package's isEmptyValue function
// determines if a value has the zero value of its type
func isZero(v reflect.Value) bool {
	switch v.Kind() {
	case reflect.Array, reflect.Map, reflect.Slice, reflect.String:
		return v.Len() == 0
	case reflect.Bool:
		return !v.Bool()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return v.Int() == 0
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		return v.Uint() == 0
	case reflect.Float32, reflect.Float64:
		return v.Float() == 0
	case reflect.Interface, reflect.Ptr, reflect.Func:
		return v.IsNil()
	case reflect.Struct:
		zero := reflect.Zero(v.Type()).Interface()
		return reflect.DeepEqual(v.Interface(), zero)
	default:
		if !v.IsValid() {
			return true
		}
		zero := reflect.Zero(v.Type())
		return v.Interface() == zero.Interface()
	}
}
