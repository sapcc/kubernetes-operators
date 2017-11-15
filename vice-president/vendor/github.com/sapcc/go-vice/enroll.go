package vice

import (
	"context"
	"net/url"
	"time"
)

const enrollBasePath = "/vswebservices/rest/services/enroll"

type _CertProductType string
type _ServerType string
type _ValidityPeriod string
type _SignatureAlgorithm string
type _CTLogOption string

type Date struct {
	time.Time
}

func (d Date) EncodeValues(key string, v *url.Values) error {
	if key != "" {
		v.Set(key, d.Format("01/02/2006"))
	}
	return nil
}

var ServerType = struct {
	Microsoft _ServerType
	OpenSSL   _ServerType
}{
	"Microsoft",
	"Apache",
}

var ValidityPeriod = struct {
	OneYear    _ValidityPeriod
	TwoYears   _ValidityPeriod
	ThreeYears _ValidityPeriod
}{
	"1Y",
	"2Y",
	"3Y",
}

var SignatureAlgorithm = struct {
	SHA1WithRSAEncryption       _SignatureAlgorithm
	SHA256WithRSAEncryption     _SignatureAlgorithm
	SHA256WithRSAEncryptionFull _SignatureAlgorithm
	DSAwithSHA256               _SignatureAlgorithm
	ECDSAwithSHA256             _SignatureAlgorithm
	ECDSAwithSHA256andRSAroot   _SignatureAlgorithm
}{
	"sha1WithRSAEncryption",
	"sha256WithRSAEncryption",
	"sha256WithRSAEncryptionFull",
	"DSAwithSHA256",
	"ECDSAwithSHA256",
	"ECDSAwithSHA256andRSAroot",
}

var CTLogOption = struct {
	Public _CTLogOption
	NoLog  _CTLogOption
}{
	"public",
	"nolog",
}

type EnrollRequest struct {
	Challenge          string              `url:"challenge"`
	FirstName          string              `url:"firstName"`
	MiddleInitial      string              `url:"middleInitial,omitempty"`
	LastName           string              `url:"lastName"`
	Email              string              `url:"email"`
	CSR                string              `url:"csr"`
	CertProductType    _CertProductType    `url:"certProductType"`
	ServerType         _ServerType         `url:"serverType"`
	ValidityPeriod     _ValidityPeriod     `url:"validityPeriod"`
	SpecificEndDate    Date                `url:"specificEndDate,omitempty"`
	EmployeeId         string              `url:"employeeID,omitempty"`
	ServerIP           string              `url:"serverIP,omitempty"`
	MailStop           string              `url:"mailStop,omitempty"`
	SignatureAlgorithm _SignatureAlgorithm `url:"signatureAlgorithm,omitempty"`
	CTLogOption        _CTLogOption        `url:"ctLogOption,omitempty"`
	AdditionalFields   []string            `url:"additionalField,numbered,omitempty"`
	SubjectAltNames    []string            `url:"subject_alt_names,comma,omitempty"`
}

type Enrollment struct {
	ViceResponse

	Certificate   string `xml:"Certificate,omitempty"`
	TransactionID string `xml:"Transaction_ID,omitempty"`
}

func (c *CertificatesServiceOp) Enroll(ctx context.Context, er *EnrollRequest) (*Enrollment, error) {
	req, err := c.client.newRequest(ctx, "POST", enrollBasePath, er)
	if err != nil {
		return nil, err
	}

	enrollment := new(Enrollment)
	err = c.client.Do(req, enrollment)
	if err != nil {
		return nil, err
	}

	return enrollment, nil
}
