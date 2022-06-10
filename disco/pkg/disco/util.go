package disco

import "strings"

// ensureFQDN ensures the recordset name ends with '.'
func ensureFQDN(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}
