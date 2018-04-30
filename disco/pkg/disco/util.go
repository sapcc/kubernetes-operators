/*******************************************************************************
*
* Copyright 2018 SAP SE
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

package disco

import (
	"fmt"
	"log"
	"os"
	"strings"

	"k8s.io/api/extensions/v1beta1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func newClientConfig(options Options) (*rest.Config, error) {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}
	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}
	return clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
}

var LogLevel = struct {
	DEBUG,
	INFO,
	ERROR,
	FATAL string
}{
	"DEBUG",
	"INFO",
	"ERROR",
	"FATAL",
}

func isDebug() bool {
	if os.Getenv("DEBUG") == "1" {
		return true
	}
	return false
}

// LogInfo logs info messages
func LogInfo(msg string, args ...interface{}) {
	doLog(
		LogLevel.INFO,
		msg,
		args,
	)
}

// LogError logs error messages
func LogError(msg string, args ...interface{}) {
	doLog(
		LogLevel.ERROR,
		msg,
		args,
	)
}

// LogDebug logs debug messages, if DEBUG is enabled
func LogDebug(msg string, args ...interface{}) {
	if isDebug() {
		doLog(
			LogLevel.DEBUG,
			msg,
			args,
		)
	}
}

// LogFatal logs debug messages, if DEBUG is enabled
func LogFatal(msg string, args ...interface{}) {
	doLog(
		LogLevel.FATAL,
		msg,
		args,
	)
}

func doLog(logLevel string, msg string, args []interface{}) {
	msg = strings.TrimPrefix(msg, "\n")
	msg = fmt.Sprintf("%s: %s", logLevel, msg)
	if logLevel == LogLevel.FATAL {
		log.Fatalf(msg+"\n", args...)
		return
	}
	if len(args) > 0 {
		log.Printf(msg+"\n", args...)
	} else {
		log.Println(msg)
	}
}

func ingressHasDiscoFinalizer(ingress *v1beta1.Ingress) bool {
	for _, fin := range ingress.GetFinalizers() {
		if fin == DiscoFinalizer {
			return true
		}
	}
	return false
}

func ingressHasDeletionTimestamp(ingress *v1beta1.Ingress) bool {
	if ingress.GetDeletionTimestamp() != nil {
		return true
	}
	return false
}

// addSuffixIfRequired ensures the recordset name ends with '.'
func addSuffixIfRequired(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}

func mergeMaps(src, dst map[string]string) map[string]string {
	if src == nil {
		return dst
	}
	if dst == nil {
		return src
	}
	for k, v := range src {
		dst[k] = v
	}
	return dst
}

func trimQuotesAndSpace(s string) string {
	if s == "" {
		return s
	}
	st := strings.Trim(s, `"`)
	return strings.TrimSpace(st)
}
