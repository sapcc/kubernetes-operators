/*******************************************************************************
*
* Copyright 2019 SAP SE
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
	"bytes"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"sort"
	"strings"

	"github.com/pkg/errors"
	"golang.org/x/crypto/ocsp"
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

func readPrivateKeyFromPEM(keyPEM []byte) (*rsa.PrivateKey, error) {
	block, _ := pem.Decode(keyPEM)
	if block == nil {
		return nil, errors.New("failed to decode public key from PEM block")
	}
	key, err := x509.ParsePKCS1PrivateKey(block.Bytes)
	if err != nil {
		return nil, errors.Wrap(err, "couldn't parse private key")
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
		return nil, errors.New("couldn't encode private key to PEM block")
	}
	return keyPEM, nil
}

func readCertificateFromPEM(certPEM []byte) (*x509.Certificate, error) {
	block, _ := pem.Decode(certPEM)
	if block == nil {
		return nil, errors.New("couldn't decode certificate from PEM block")
	}
	if block.Type != CertificateType {
		return nil, errors.New("certificate contains invalid date")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to parse certificate")
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
		return nil, errors.New("couldn't encode certificates")
	}
	return certPEMs, nil
}

func readCertFromFile(filePath string) (*x509.Certificate, error) {
	certPEM, err := ioutil.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	return readCertificateFromPEM(certPEM)
}

func removeSpecialCharactersFromPEM(pem []byte) []byte {
	specialChars := []string{"\"", "^@", "\x00", "0"}
	var result []byte
	for _, c := range specialChars {
		result = bytes.TrimLeft(pem, fmt.Sprintf("%q\n", c))
	}
	return result
}

func contains(stringSlice []string, searchString string) bool {
	for _, value := range stringSlice {
		if value == searchString {
			return true
		}
	}
	return false
}

func ocspRevokationReasonToString(status int) string {
	switch status {
	case ocsp.Unspecified:
		return "unspecified"
	case ocsp.KeyCompromise:
		return "key compromise"
	case ocsp.CACompromise:
		return "ca compromise"
	case ocsp.AffiliationChanged:
		return "affiliation changed"
	case ocsp.Superseded:
		return "superseded"
	case ocsp.CessationOfOperation:
		return "cessation of operation"
	case ocsp.CertificateHold:
		return "certificate hold"
	}
	return "unknown"
}

func ocspStatusToString(status int) string {
	switch status {
	case ocsp.Good:
		return "good"
	case ocsp.Revoked:
		return "revoked"
	case ocsp.Unknown:
		return "unknown"
	case ocsp.ServerFailed:
		return "server failed"
	}
	return "unknown"
}

func downloadAndPersistFile(CAURI string, filePath string) ([]byte, error) {
	resp, err := http.Get(CAURI)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	bytes, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	return saveToFile(bytes, filePath)
}

func getFileNameFromURI(URI string) string {
	f := strings.Split(URI, "/")
	return f[len(f)-1]
}

func isStringSlicesEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}

	aCopy := make([]string, len(a))
	copy(aCopy, a)

	bCopy := make([]string, len(b))
	copy(bCopy, b)

	sort.Strings(aCopy)
	sort.Strings(bCopy)

	for idx, val := range aCopy {
		if bCopy[idx] != val {
			return false
		}
	}
	return true
}

func saveToFile(contentBytes []byte, filePath string) ([]byte, error) {
	out, err := os.Create(filePath)
	if err != nil {
		return nil, err
	}
	defer out.Close()

	_, err = out.Write(contentBytes)
	if err != nil {
		return nil, err
	}

	return contentBytes, nil
}

func keyFunc(namespace, name string) string {
	return fmt.Sprintf("%s/%s", namespace, name)
}
