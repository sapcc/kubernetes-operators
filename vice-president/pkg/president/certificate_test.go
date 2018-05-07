package president

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"

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

func (s *TestSuite) TestBase64Encoding() {
	certPEM, err := writeCertificatesToPEM([]*x509.Certificate{s.ViceCert.Certificate})
	s.Require().NoError(err, "writing a certificate to PEM should not cause an error")
	s.Require().NotNil(certPEM, "PEM encoded certificate should not be nil")

	expected := []byte("LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURaekNDQWsrZ0F3SUJBZ0lKQVBoell3SENNMjdwTUEwR0NTcUdTSWIzRFFFQkJRVUFNRTh4Q3pBSkJnTlYKQkFZVEFrTk9NUXN3Q1FZRFZRUUlFd0pIUkRFTE1Ba0dBMVVFQnhNQ1Uxb3hFekFSQmdOVkJBb1RDa0ZqYldVcwpJRWx1WXk0eEVUQVBCZ05WQkFNVENFMTVVbTl2ZEVOQk1CNFhEVEUzTVRBeE56QXlOREF5TTFvWERURTNNVEF5Ck56QXlOREF5TTFvd1ZqRUxNQWtHQTFVRUJoTUNRMDR4Q3pBSkJnTlZCQWdUQWtkRU1Rc3dDUVlEVlFRSEV3SlQKV2pFVE1CRUdBMVVFQ2hNS1FXTnRaU3dnU1c1akxqRVlNQllHQTFVRUF4TVBkM2QzTG1WNFlXMXdiR1V1WTI5dApNSUlCSWpBTkJna3Foa2lHOXcwQkFRRUZBQU9DQVE4QU1JSUJDZ0tDQVFFQXBQUFRMZ3BBSWtsdHFCWm9nbit5CkQ0OFBOS1YrNzBOOTh5aWo4ei9UenRCd3RZaWxOVVN4bGtGZnkzUjl3Y2FmcGw5a3BUeGtSTUh1L3JJNmZDbk8KeExhemtURVZiTFJyWXFUN2FiZ0Yzei93dFlFeFhheElwSnQyaEtYelcvOWZEVDhYbGFrUHFXL1lLQUhDaHZTQQpNMEtUSmtaZzJKVllQb2V0QVM1VmxtdTRZNXZaZWwwWnpiMitJMldLMTFpZkFEQlpOWDYvOWxYTVZKNWN3TzhYCnk0cy9UZGNwMzNhSWJoT0hiK2RyOHNNdWlwRzQwRDBwV0NtTWJWQ2RGd0Z6L0o3cGczZTFMaVh2elI3Si8wQ2IKYVRmNWdUaVYxTW4xWVJsQ1VDQkdaN2c1MExhbmI2WG5hTHRjV2s1S1ZrOGxubTFPcTd1L1F6TVNrS3pWSHpMdwpWUUlEQVFBQm96OHdQVEE3QmdOVkhSRUVOREF5Z2d0bGVHRnRjR3hsTG1OdmJZSVBkM2QzTG1WNFlXMXdiR1V1ClkyOXRnaEozZDNjdWJYa3RaWGhoYlhCc1pTNWpiMjB3RFFZSktvWklodmNOQVFFRkJRQURnZ0VCQUwva29VangKU2x0WEJXZ3RXL2JlV3FxdnB0a25LQ2lKSzNlMW9sMnIyWVNTV3BLK2dyMFlpRDlNeFN0MklDSnZXZmF0L3FLTQpFTGwzUzVEQlRmckRQRk12RmVEOTZkc1VuKytOSXpSa3pXUndxaUlmZ1VoOWpHdnhyTkJwOHcydDRLOTUzUkwxCnVQTmdKbjA5R1JTWDNQRXdyNlhqN1pQb3VOMWQvOGJLQVRlVC9NWXBNTmhHSjBrMmZpekU4UTZ6dVp5eXZCZ1kKNEJXVzh1L1dyS1BFcWozZS9sRHdxU1Rha0J5eXZNZS8rWmVPdFhvMjdBRXdDNEpRK21FYXl3THV6bEgvSnRtdAplN2lJN1RpdVE1U2QzL0F3OXlCeXAxTldLRWY1bElVc1FGNzNiODNTN01CRFNRS3R5QUhESmU1WFJQRHNmYmFjCnJSOGJiZzJHVGZOZkg2UT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=")
	b64Enc, err := base64Encode(certPEM)
	s.Assert().NoError(err)
	s.Assert().Equal(expected, b64Enc)
}
