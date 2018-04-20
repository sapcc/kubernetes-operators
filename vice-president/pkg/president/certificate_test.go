package president

import (
	"crypto/rand"
	"crypto/rsa"

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

	s.Equal( slice.SortStrings(vc.sans), slice.SortStrings(sansWithHost))
	s.Equal( slice.SortStrings(vc1.sans), slice.SortStrings(sansWithHost))

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
		)
	}
}

func (s *TestSuite) TestCertificateAndHostMatch() {

	s.ViceCert.Host = "invalid.com"
	s.False(s.ViceCert.DoesCertificateAndHostMatch())

	s.ViceCert.Host = "example.com"
	s.True(s.ViceCert.DoesCertificateAndHostMatch())

	san := "www.my-example.com"
	s.ViceCert.SetSANs([]string{san})
	s.True(s.ViceCert.DoesCertificateAndHostMatch())
	s.Contains(s.ViceCert.Certificate.DNSNames, san)
}

func (s *TestSuite) TestDoesKeyAndCertificateTally() {

	randomKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		s.T().Errorf("Couldn't generate random key. %s", err.Error())
	}

	s.True(s.ViceCert.DoesKeyAndCertificateTally())

	s.ViceCert.PrivateKey = randomKey
	s.False(s.ViceCert.DoesKeyAndCertificateTally())

}

func (s *TestSuite) TestDoesCertificateExpireSoon() {

	s.True(s.ViceCert.DoesCertificateExpireSoon())

}
