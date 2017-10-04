/*******************************************************************************
*
* Copyright 2017 SAP SE
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

package president

import (
	"strings"

	apierrors "k8s.io/apimachinery/pkg/api/errors"

	"bytes"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"io/ioutil"
	"log"
	"os"
)

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

func readPrivateKeyFromPEM(keyPEM []byte) (*rsa.PrivateKey, error) {
	block, _ := pem.Decode(keyPEM)
	if block == nil {
		return nil, fmt.Errorf("Failed to decode public key from PEM block: %#v", keyPEM)
	}
	key, err := x509.ParsePKCS1PrivateKey(block.Bytes)
	if err != nil {
		LogError("Could not parse private key: %s", err.Error())
		return nil, err
	}
	return key, nil
}

func writePrivateKeyToPEM(key *rsa.PrivateKey) ([]byte, error) {
	keyPEM := pem.EncodeToMemory(
		&pem.Block{
			Type:    PrivateKeyType,
			Headers: nil,
			Bytes:   x509.MarshalPKCS1PrivateKey(key),
		},
	)
	if keyPEM == nil {
		return nil, fmt.Errorf("Couldn't encode private key to PEM: %#v", key)
	}
	return keyPEM, nil
}

func readCertificateFromPEM(certPEM []byte) (*x509.Certificate, error) {
	block, _ := pem.Decode(certPEM)
	if block == nil {
		return nil, fmt.Errorf("Failed to decode certificate from PEM block: %s", string(certPEM))
	}
	if block.Type != CertificateType {
		return nil, fmt.Errorf("Certificate contains invalid data: %#v", block)
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		LogError("Failed to parse certificate: %s", err.Error())
		return nil, err
	}
	return cert, nil
}

func writeCertificatesToPEM(certs []*x509.Certificate) ([]byte, error) {
  certPEMs := []byte{}

	for _, c := range certs {
		certByte := removeSpecialCharactersFromPEM(
			pem.EncodeToMemory(
				&pem.Block{
					Type:  CertificateType,
					Bytes: c.Raw,
				},
			),
		)
		for _, b := range certByte {
			certPEMs = append(certPEMs, b)
		}
	}

	if certPEMs == nil {
		return nil, fmt.Errorf("Couldn't encode certificate %#v", certPEMs)
	}
	return certPEMs, nil
}

func readCertFromFile(filePath string) (*x509.Certificate, error) {
	certPEM, err := ioutil.ReadFile(filePath)
	if err != nil {
		log.Printf("Couldn't read file. %s", err)
		return nil, err
	}
	return readCertificateFromPEM(certPEM)
}

func readKeyFromFile(filePath string) (*rsa.PrivateKey, error) {
	keyRaw, err := ioutil.ReadFile(filePath)
	if err != nil {
		LogError("Couldn't read file. %s", err)
		return nil, err
	}
	key, err := x509.ParsePKCS1PrivateKey(keyRaw)
	if err != nil {
		LogError("Couldn't parse key. %s", err)
		return nil, err
	}
	return key, nil
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
	specialChars := []string{"\"", "^@","\x00", "0"}
	var result []byte
	for _, c := range specialChars {
		result = bytes.TrimLeft(pem, fmt.Sprintf("%q\n", c))
	}
	return result
}
