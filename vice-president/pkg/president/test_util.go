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
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	log2 "github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"path"
	"time"

	"fmt"
	"os"

	"strconv"

	"github.com/stretchr/testify/suite"
	"k8s.io/client-go/pkg/api/v1"

	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
)

// FIXTURES path to the subfolder containing fixtures
const FIXTURES = "fixtures"

// TESTPORT the port used by the MockServer
const TESTPORT = 8001

// TestSuite ..
type TestSuite struct {
	suite.Suite
	VP                   *Operator
	HTTPMux              *http.ServeMux
	TestPort             int
	Cert                 *x509.Certificate
	CertByte             []byte
	Key                  *rsa.PrivateKey
	KeyByte              []byte
	Secret               *v1.Secret
	ViceCert             *ViceCertificate
	IntermediateCertByte []byte
}

// SetupMockEndpoints defines the endpoints available during mock tests
func (s *TestSuite) SetupMockEndpoints() {
	headersEnroll := map[string]string{
		"Content-Type":   "application/xml;charset=UTF-8",
		"Content-Length": "2042",
	}

	s.respondWith("/vswebservices/rest/services/enroll", 200, headersEnroll, "enrollCertificateResponse.xml")

	headersRenew := map[string]string{
		"Content-Type":   "text/xml;charset=UTF-8",
		"Content-Length": "1761",
	}
	s.respondWith("/vswebservices/rest/services/renew", 200, headersRenew, "renewCertificateResponse.xml")

	headersApprove := map[string]string{
		"Content-Type":   "text/xml;charset=UTF-8",
		"Content-Length": "1761",
	}
	s.respondWith("/vswebservices/rest/services/approve", 200, headersApprove, "approveCertificateResponse.xml")

	headersPickup := map[string]string{
		"Content-Type":   "text/xml;charset=UTF-8",
		"Content-Length": "1761",
	}
	s.respondWith("/vswebservices/rest/services/pickup", 200, headersPickup, "pickupCertificateResponse.xml")
}

// SetupSuite creates a new testsuite
func (s *TestSuite) SetupSuite() {
	s.T().Logf("Initializing TestSuite")
	testPort := strconv.Itoa(TESTPORT)
	var err error

	//read cert from fixtures
	s.CertByte, err = s.readFixture("example.pem")
	if err != nil {
		log.Printf("Couldn't read example.pem")
	}
	certBlock, _ := pem.Decode(s.CertByte)
	if certBlock == nil {
		s.T().Errorf("failed to decode PEM block containing certificate.")
	}
	s.Cert, err = x509.ParseCertificate(certBlock.Bytes)
	if err != nil {
		s.T().Errorf("failed to parse certificate: %s", err.Error())
	}

	s.IntermediateCertByte, err = s.readFixture("intermediate.pem")
	if err != nil {
		log.Fatalf("Coulnd't load intermediate.pem")
	}

	//read private key from fixtures
	s.KeyByte, err = s.readFixture("example.key")
	if err != nil {
		log.Printf("Couldn't read example.key")
	}
	keyBlock, _ := pem.Decode(s.KeyByte)
	if keyBlock == nil {
		s.T().Errorf("Failed to decode PEM block containing the public key")
	}
	s.Key, err = x509.ParsePKCS1PrivateKey(keyBlock.Bytes)
	if err != nil {
		s.T().Errorf("Could not parse private key: %s", err.Error())
	}

	intermediateCert, err := readCertFromFile(path.Join(FIXTURES, "intermediate.pem"))
	if err != nil {
		s.T().Error(err)
	}

	s.ViceCert = NewViceCertificate(
		&v1beta1.Ingress{
			ObjectMeta: meta_v1.ObjectMeta{
				Namespace: "default",
				Name:      "my-ingress",
			},
		},
		"my-secret",
		"www.example.com",
		[]string{"www.example.com"},
		intermediateCert,
		&x509.CertPool{},
	)
	s.ViceCert.privateKey = s.Key
	s.ViceCert.certificate = s.Cert

	s.Secret = &v1.Secret{
		Type: v1.SecretTypeOpaque,
		Data: map[string][]byte{
			SecretTLSCertType: append(s.IntermediateCertByte, s.CertByte...),
			SecretTLSKeyType:  s.KeyByte,
		},
		ObjectMeta: meta_v1.ObjectMeta{
			Namespace: "default",
			Name:      "my-secret",
		},
	}

	opts := Options{
		ViceCrtFile:             "fixtures/example.pem",
		ViceKeyFile:             "fixtures/example.key",
		VicePresidentConfig:     "fixtures/example.vicepresidentconfig",
		KubeConfig:              "fixtures/example.kubeconfig",
		IntermediateCertificate: "fixtures/intermediate.pem",
	}

	//create vice president
	s.VP = New(opts, log2.NewLogger(true))

	s.VP.viceClient.BaseURL, _ = url.Parse(fmt.Sprintf("http://localhost:%s", testPort))

	go s.setupMockServer(testPort)
	time.Sleep(2 * time.Second)
}

// TearDownSuite tears down the testsuite
func (s *TestSuite) TearDownSuite() {
	s.T().Logf("Shutting down TestSuite.")
}

func (s *TestSuite) setupMockServer(port string) {
	s.T().Logf("Starting local mockserver on port %s.", port)
	s.HTTPMux = http.NewServeMux()

	s.SetupMockEndpoints()

	if err := http.ListenAndServe(fmt.Sprintf(":%s", port), s.HTTPMux); err != nil {
		s.T().Errorf(err.Error())
	}
}

func (s *TestSuite) readFixture(fileName string) (file []byte, err error) {
	pwd, err := os.Getwd()
	if err != nil {
		s.T().Errorf("Couldn't get current path. %s", err)
		return nil, err
	}
	fullPath := path.Join(pwd, FIXTURES, fileName)
	file, err = ioutil.ReadFile(fullPath)
	if err != nil {
		s.T().Errorf("Couldn't load file %s. %s", fullPath, err)
		return nil, err
	}
	return file, nil
}

func (s *TestSuite) respondWith(endpoint string, responseCode int, headers map[string]string, filePath string) {

	var _headers map[string]string

	fileContent, err := s.readFixture(filePath)
	if err != nil {
		s.T().Errorf("Couldn't find fixture %s: %s.", filePath, err)
		return
	}

	if headers == nil {
		_headers = map[string]string{
			"Content-Type": "application/json, */*",
			"Encoding":     "gzip",
		}
	} else {
		_headers = headers
	}

	s.HTTPMux.HandleFunc(endpoint, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(responseCode)
		for k, v := range _headers {
			w.Header().Set(k, v)
		}
		w.Write(fileContent)
	})
}

// ResetIngressInformerStoreAndAddIngress clears the ingress informer store and adds the given ingress
func (s *TestSuite) ResetIngressInformerStoreAndAddIngress(ingress *v1beta1.Ingress) error {
	for _, v := range s.VP.ingressInformer.GetStore().List() {
		if err := s.VP.ingressInformer.GetStore().Delete(v); err != nil {
			return err
		}
	}
	if ingress != nil {
		return s.VP.ingressInformer.GetStore().Add(ingress)
	}
	return nil
}
