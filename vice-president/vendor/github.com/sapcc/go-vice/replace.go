package vice

import (
	"context"
)

const replaceBasePath = "/vswebservices/rest/services/replace"

type ReplaceRequest struct {
	OriginalCertificate   string `url:"original_certificate"`
	OriginalTransactionID string `url:"original_transaction_id,omitempty"`
	OriginalChallenge     string `url:"original_challenge"`
	Challenge             string `url:"challenge"`
	Reason                string `url:"reason"`
	CSR                   string `url:"csr"`
	SpecificEndDate       Date   `url:"specificEndDate,omitempty"`

	FirstName          string              `url:"firstName"`
	LastName           string              `url:"lastName"`
	Email              string              `url:"email"`
	ServerType         _ServerType         `url:"serverType"`
	SignatureAlgorithm _SignatureAlgorithm `url:"signatureAlgorithm,omitempty"`
	CTLogOption        _CTLogOption        `url:"ctLogOption,omitempty"`
	AdditionalFields   []string            `url:"additionalField,numbered,omitempty"`
}

type Replacement struct {
	ViceResponse

	Certificate   string `xml:"Certificate,omitempty"`
	TransactionID string `xml:"Transaction_ID,omitempty"`
}

func (c *CertificatesServiceOp) Replace(ctx context.Context, er *ReplaceRequest) (*Replacement, error) {
	req, err := c.client.newRequest(ctx, "POST", replaceBasePath, er)
	if err != nil {
		return nil, err
	}

	replacement := new(Replacement)
	err = c.client.Do(req, replacement)
	if err != nil {
		return nil, err
	}

	return replacement, nil
}
