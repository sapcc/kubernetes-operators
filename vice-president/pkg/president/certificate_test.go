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
	"crypto/rand"
	"crypto/rsa"
	"io/ioutil"
	"path"
	"sort"
	"time"
)

func (s *TestSuite) TestSetSANS() {

	host := "example.com"

	sansWithoutHost := []string{"my-example.com"}
	sansWithHost := []string{"example.com", "my-example.com"}

	vc := ViceCertificate{host: host}
	vc.setSANs(sansWithHost)

	vc1 := ViceCertificate{host: host}
	vc1.setSANs(sansWithoutHost)

	s.Equal(sortedStringSlice(vc.sans), sortedStringSlice(sansWithHost))
	s.Equal(sortedStringSlice(vc1.sans), sortedStringSlice(sansWithHost))

}

func (s *TestSuite) TestGetSANS() {
	testViceCertificates := map[*ViceCertificate][]string{
		&ViceCertificate{}:                    {""},
		&ViceCertificate{host: ""}:            {""},
		&ViceCertificate{host: "example.com"}: {"example.com"},
		&ViceCertificate{host: "example.com", sans: []string{"my-example.com"}}: {"example.com", "my-example.com"},
	}

	for viceCert, expectedSANS := range testViceCertificates {
		s.Equal(
			sortedStringSlice(expectedSANS),
			sortedStringSlice(viceCert.getSANs()),
			"SANs should be equal",
		)
	}
}

func (s *TestSuite) TestCertificateAndHostMatch() {
	s.ViceCert.host = "invalid.com"
	s.False(s.ViceCert.DoesCertificateAndHostMatch(), "certificate common name shouldn't match 'invalid.com'")

	s.ViceCert.host = "example.com"
	s.ViceCert.sans = []string{"example.com", "www.example.com", "www.my-example.com"}
	s.True(s.ViceCert.DoesCertificateAndHostMatch(), "certificate common name and host should match")
}

func (s *TestSuite) TestDoesKeyAndCertificateTally() {
	randomKey, err := rsa.GenerateKey(rand.Reader, 2048)
	s.Require().NoError(err, "there should be no error generating a random key")

	s.True(s.ViceCert.DoesKeyAndCertificateTally(), "certificate and private key should tally")

	s.ViceCert.privateKey = randomKey
	s.False(s.ViceCert.DoesKeyAndCertificateTally(), "certificate and random private key shouldn't tally")

}

func (s *TestSuite) TestDoesCertificateExpireSoon() {
	vc := s.ViceCert
	minCertValidityDays := s.VP.Options.MinCertValidityDays

	vc.certificate.NotAfter = time.Now().AddDate(0, 0, -1)
	s.True(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be true to indicate the certificate was valid until yesterday and has to be renewed",
	)

	vc.certificate.NotAfter = time.Now().AddDate(0, -1, 0)
	s.True(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be true to indicate the certificate was valid until last month and has to be renewed",
	)

	vc.certificate.NotAfter = time.Now().AddDate(0, 0, 29)
	s.True(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be true to indicate the certificate is valid for 1 month and has to be renewed",
	)

	vc.certificate.NotAfter = time.Now().AddDate(0, 1, 1)
	s.False(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be false to indicate the certificate is valid for more than 1 month. no renewal needed",
	)

	vc.certificate.NotAfter = time.Now().AddDate(0, 6, 0)
	s.False(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be false to indicate the certificate is valid for another 6 month. no renewal needed",
	)
}

func (s *TestSuite) TestWriteCertificateChain() {
	expectedChainPEM, err := ioutil.ReadFile(path.Join(FIXTURES, "chain.pem"))

	chainPEM, err := writeCertificatesToPEM(
		s.ViceCert.withIntermediateCertificate(),
	)
	s.NoError(err, "there should be no error writing a certificate to PEM format")

	s.Equal(expectedChainPEM, removeSpecialCharactersFromPEM(chainPEM))
}

func sortedStringSlice(s []string) []string {
	sort.Strings(s)
	return s
}
