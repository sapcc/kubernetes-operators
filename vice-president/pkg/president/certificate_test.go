package president

import (
	"crypto/rand"
	"crypto/rsa"

	"github.com/stretchr/testify/assert"
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

	assert.Equal(s.T(), slice.SortStrings(vc.sans), slice.SortStrings(sansWithHost))
	assert.Equal(s.T(), slice.SortStrings(vc1.sans), slice.SortStrings(sansWithHost))

}

func (s *TestSuite) TestGetSANS() {
	testViceCertificates := map[*ViceCertificate][]string{
		&ViceCertificate{}:                                                      {""},
		&ViceCertificate{Host: ""}:                                              {""},
		&ViceCertificate{Host: "example.com"}:                                   {"example.com"},
		&ViceCertificate{Host: "example.com", sans: []string{"my-example.com"}}: {"example.com", "my-example.com"},
	}

	for viceCert, expectedSANS := range testViceCertificates {
		assert.Equal(s.T(),
			slice.SortStrings(expectedSANS),
			slice.SortStrings(viceCert.GetSANs()),
		)
	}
}

func (s *TestSuite) TestCertificateAndHostMatch() {

	s.ViceCert.Host = "invalid.com"
	assert.False(s.T(), s.ViceCert.DoesCertificateAndHostMatch())

	s.ViceCert.Host = "example.com"
	assert.True(s.T(), s.ViceCert.DoesCertificateAndHostMatch())

	san := "www.my-example.com"
	s.ViceCert.SetSANs([]string{san})
	assert.True(s.T(), s.ViceCert.DoesCertificateAndHostMatch())
	assert.Contains(s.T(), s.ViceCert.Certificate.DNSNames, san)
}

func (s *TestSuite) TestDoesKeyAndCertificateTally() {

	randomKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		s.T().Errorf("Couldn't generate random key. %s", err.Error())
	}

	assert.True(s.T(), s.ViceCert.DoesKeyAndCertificateTally())

	s.ViceCert.PrivateKey = randomKey
	assert.False(s.T(), s.ViceCert.DoesKeyAndCertificateTally())

}

func (s *TestSuite) TestDoesCertificateExpireSoon() {

	assert.True(s.T(), s.ViceCert.DoesCertificateExpireSoon())

}
