package president

import (
	"crypto/rand"
	"crypto/rsa"
	"io/ioutil"
	"path"
	"time"

	"k8s.io/kubernetes/pkg/util/slice"
)

func (s *TestSuite) TestSetSANS() {

	host := "example.com"

	sansWithoutHost := []string{"my-example.com"}
	sansWithHost := []string{"example.com", "my-example.com"}

	vc := ViceCertificate{Host: host}
	vc.SetSANs(sansWithHost)

	vc1 := ViceCertificate{Host: host}
	vc1.SetSANs(sansWithoutHost)

	s.Equal(slice.SortStrings(vc.sans), slice.SortStrings(sansWithHost))
	s.Equal(slice.SortStrings(vc1.sans), slice.SortStrings(sansWithHost))

}

func (s *TestSuite) TestGetSANS() {
	testViceCertificates := map[*ViceCertificate][]string{
		&ViceCertificate{}:                                                      {""},
		&ViceCertificate{Host: ""}:                                              {""},
		&ViceCertificate{Host: "example.com"}:                                   {"example.com"},
		&ViceCertificate{Host: "example.com", sans: []string{"my-example.com"}}: {"example.com", "my-example.com"},
	}

	for viceCert, expectedSANS := range testViceCertificates {
		s.Equal(
			slice.SortStrings(expectedSANS),
			slice.SortStrings(viceCert.GetSANs()),
			"SANs should be equal",
		)
	}
}

func (s *TestSuite) TestCertificateAndHostMatch() {

	s.ViceCert.Host = "invalid.com"
	s.False(s.ViceCert.DoesCertificateAndHostMatch(), "certificate common name shouldn't match 'invalid.com'")

	s.ViceCert.Host = "example.com"
	s.True(s.ViceCert.DoesCertificateAndHostMatch(), "certificate common name and host should match")

	san := "www.my-example.com"
	s.ViceCert.SetSANs([]string{san})
	s.True(s.ViceCert.DoesCertificateAndHostMatch(), "certificate common name and host should match")
	s.Contains(s.ViceCert.Certificate.DNSNames, san)
}

func (s *TestSuite) TestDoesKeyAndCertificateTally() {
	randomKey, err := rsa.GenerateKey(rand.Reader, 2048)
	s.Require().NoError(err, "there should be no error generating a random key")

	s.True(s.ViceCert.DoesKeyAndCertificateTally(), "certificate and private key should tally")

	s.ViceCert.PrivateKey = randomKey
	s.False(s.ViceCert.DoesKeyAndCertificateTally(), "certificate and random private key shouldn't tally")

}

func (s *TestSuite) TestDoesCertificateExpireSoon() {
	vc := s.ViceCert
	minCertValidityDays := s.VP.Options.MinCertValidityDays

	vc.Certificate.NotAfter = time.Now().AddDate(0, 0, -1)
	s.True(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be true to indicate the certificate was valid until yesterday and has to be renewed",
	)

	vc.Certificate.NotAfter = time.Now().AddDate(0, -1, 0)
	s.True(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be true to indicate the certificate was valid until last month and has to be renewed",
	)

	vc.Certificate.NotAfter = time.Now().AddDate(0, 1, 0)
	s.True(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be true to indicate the certificate is valid for 1 month and has to be renewed",
	)

	vc.Certificate.NotAfter = time.Now().AddDate(0, 1, 1)
	s.False(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be false to indicate the certificate is valid for more than 1 month. no renewal needed",
	)

	vc.Certificate.NotAfter = time.Now().AddDate(0, 6, 0)
	s.False(
		s.ViceCert.DoesCertificateExpireSoon(minCertValidityDays),
		"should be false to indicate the certificate is valid for another 6 month. no renewal needed",
	)
}

func (s *TestSuite) TestWriteCertificateChain() {
	expectedChainPEM, err := ioutil.ReadFile(path.Join(FIXTURES, "chain.pem"))

	chainPEM, err := writeCertificatesToPEM(
		s.ViceCert.WithIntermediateCertificate(),
	)
	s.NoError(err, "there should be no error writing a certificate to PEM format")

	s.Equal(expectedChainPEM, removeSpecialCharactersFromPEM(chainPEM))
}
