package disco

import (
	"strings"
)

// RecordsetType defines the types of recordsets
var RecordsetType = struct {
	CNAME string
}{
	"CNAME",
}

// addSuffixIfRequired ensures the recordset name ends with '.'
func addSuffixIfRequired(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}
