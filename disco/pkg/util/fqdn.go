package controllers

import (
	"strings"
)

// EnsureFQDN ensures the given name has a trailing '.'
func EnsureFQDN(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}
