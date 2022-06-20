package version

import (
	"bytes"
	"runtime"
	"strings"
	"text/template"
)

var (
	GitCommit string
	GitState  string
	GitBranch string
	BuildDate string
	GoVersion = runtime.Version()
)

var versionInfoTmpl = `
{{.program}}, branch: {{.branch}}, revision: {{.revision}} ({{.state}})
  build date:       {{.buildDate}}
  go version:       {{.goVersion}}
`

// Print returns the version information.
func Print(program string) string {
	m := map[string]string{
		"program":   program,
		"branch":    GitBranch,
		"revision":  GitCommit,
		"state":     GitState,
		"buildDate": BuildDate,
		"goVersion": GoVersion,
	}
	t := template.Must(template.New("version").Parse(versionInfoTmpl))

	var buf bytes.Buffer
	if err := t.ExecuteTemplate(&buf, "version", m); err != nil {
		panic(err)
	}
	return strings.TrimSpace(buf.String())
}
