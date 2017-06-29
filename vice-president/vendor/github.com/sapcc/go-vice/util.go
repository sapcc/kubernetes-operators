package vice

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/asn1"
	"encoding/pem"
	"net"
)

func CreateCSR(name pkix.Name, email string, sans []string, key *rsa.PrivateKey) ([]byte, error) {
	rawSubject, err := asn1.Marshal(name.ToRDNSequence())
	if err != nil {
		return nil, err
	}

	template := x509.CertificateRequest{
		RawSubject:         rawSubject,
		EmailAddresses:     []string{email},
		SignatureAlgorithm: x509.SHA256WithRSA,
	}

	if len(sans) > 0 {
		rawSANS, err := marshalSANs(sans, nil, nil)
		if err != nil {
			return nil, err
		}

		template.ExtraExtensions = []pkix.Extension{
			pkix.Extension{
				Id:    []int{2, 5, 29, 17},
				Value: rawSANS,
			},
		}
	}

	csr, err := x509.CreateCertificateRequest(rand.Reader, &template, key)

	if err != nil {
		return nil, err
	}

	block := pem.Block{
		Type:  "CERTIFICATE REQUEST",
		Bytes: csr,
	}

	return pem.EncodeToMemory(&block), nil
}

func marshalSANs(dnsNames, emailAddresses []string, ipAddresses []net.IP) (derBytes []byte, err error) {
	var rawValues []asn1.RawValue
	for _, name := range dnsNames {
		rawValues = append(rawValues, asn1.RawValue{Tag: 2, Class: 2, Bytes: []byte(name)})
	}
	for _, email := range emailAddresses {
		rawValues = append(rawValues, asn1.RawValue{Tag: 1, Class: 2, Bytes: []byte(email)})
	}
	for _, rawIP := range ipAddresses {
		ip := rawIP.To4()
		if ip == nil {
			ip = rawIP
		}
		rawValues = append(rawValues, asn1.RawValue{Tag: 7, Class: 2, Bytes: ip})
	}
	return asn1.Marshal(rawValues)
}
