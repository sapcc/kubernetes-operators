package controllers

import (
	"fmt"
	"strings"

	"sigs.k8s.io/controller-runtime/pkg/client"
)

func makeAnnotation(prefix, annotationKey string) string {
	return fmt.Sprintf("%s/%s", prefix, annotationKey)
}

func isHandleObject(annotationKey string, o client.Object) bool {
	if o.GetAnnotations() == nil {
		return false
	}
	v, ok := o.GetAnnotations()[annotationKey]
	return ok && v == "true"
}

func appendIfNotContains(theStringSlice []string, theString string) []string {
	for _, s := range theStringSlice {
		if s == theString {
			return theStringSlice
		}
	}
	return append(theStringSlice, theString)
}

// ensureFQDN ensures the recordset name ends with '.'
func ensureFQDN(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}
