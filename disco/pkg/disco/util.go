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
	"strings"

	apierrors "k8s.io/apimachinery/pkg/api/errors"

	"bytes"
	"fmt"
	"log"
	"os"
)

func isAnyStringEmpty(s ...string) bool {
	if s != nil {
		for _, str := range s {
			if str == "" {
				return true
			}
		}
	}
	return false
}

func checkError(err error) error {
	if err != nil {
		if apierrors.IsAlreadyExists(err) {
			return fmt.Errorf("Does already exist")
		} else if apierrors.IsNotFound(err) {
			return fmt.Errorf("Not found")
		}
		return err
	}
	return nil
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
		"INFO",
		msg,
		args,
	)
}

// LogError logs error messages
func LogError(msg string, args ...interface{}) {
	doLog(
		"ERROR",
		msg,
		args,
	)
}

// LogDebug logs debug messages, if DEBUG is enabled
func LogDebug(msg string, args ...interface{}) {
	if isDebug() {
		doLog(
			"DEBUG",
			msg,
			args,
		)
	}
}

// LogFatal logs debug messages, if DEBUG is enabled
func LogFatal(msg string, args ...interface{}) {
	if isDebug() {
		doLog(
			"FATAL",
			msg,
			args,
		)
	}
}

func doLog(logLevel string, msg string, args []interface{}) {
	msg = strings.TrimPrefix(msg, "\n")
	msg = strings.Replace(msg, "\n", "\\n", -1) //avoid multiline log messages
	msg = fmt.Sprintf("%s: %s", logLevel, msg)
	if logLevel == "FATAL" {
		log.Fatalf(msg+"\n", args...)
		return
	}
	if len(args) > 0 {
		log.Printf(msg+"\n", args...)
	} else {
		log.Println(msg)
	}
}

func removeSpecialCharactersFromPEM(pem []byte) []byte {
	specialChars := []string{"\"", "^@", "\x00", "0"}
	var result []byte
	for _, c := range specialChars {
		result = bytes.TrimLeft(pem, fmt.Sprintf("%q\n", c))
	}
	return result
}
