package seeder

import (
	"github.com/golang/glog"
	"reflect"
)

func MergeSimpleStructFields(dst, src interface{}) {
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
		case reflect.Slice:
			continue
		case reflect.Struct:
			continue
		default:
			glog.Error("unsupported type encountered in merge of ", f.Name, ": ", f.Type.Kind())
		}
	}
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
