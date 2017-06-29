package vice

import (
	"context"
)

const renewBasePath = "/vswebservices/rest/services/renew"

type RenewRequest struct {
	Challenge             string              `url:"challenge"`
	FirstName             string              `url:"firstName"`
	LastName              string              `url:"lastName"`
	Email                 string              `url:"email"`
	CSR                   string              `url:"csr"`
	CertProductType       _CertProductType    `url:"certProductType"`
	ServerType            _ServerType         `url:"serverType"`
	ValidityPeriod        _ValidityPeriod     `url:"validityPeriod"`
	SpecificEndDate       Date                `url:"specificEndDate,omitempty"`
	OriginalCertificate   string              `url:"original_certificate"`
	OriginalTransactionID string              `url:"original_transaction_id"`
	OriginalChallenge     string              `url:"original_challenge"`
	SignatureAlgorithm    _SignatureAlgorithm `url:"signatureAlgorithm,omitempty"`
	CTLogOption           _CTLogOption        `url:"ctLogOption,omitempty"`
	SubjectAltNames       []string            `url:"subject_alt_names,comma,omitempty"`
}

type Renewal struct {
	ViceResponse

	Certificate   string `xml:"Certificate,omitempty"`
	TransactionID string `xml:"Transaction_ID,omitempty"`
}

func (c *CertificatesServiceOp) Renew(ctx context.Context, er *RenewRequest) (*Renewal, error) {
	req, err := c.client.newRequest(ctx, "POST", renewBasePath, er)
	if err != nil {
		return nil, err
	}

	renewal := new(Renewal)
	err = c.client.Do(req, renewal)
	if err != nil {
		return nil, err
	}

	return renewal, nil
}
