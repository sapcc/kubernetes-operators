package vice

import (
	"context"
	"encoding/xml"
	"fmt"
	"time"
)

const getOrgInfoBasePath = "/vswebservices/rest/services/getOrgInfo"

type SimpleTime struct {
	time.Time
}

func (sT *SimpleTime) UnmarshalXML(d *xml.Decoder, start xml.StartElement) error {
	const shortForm = "01/02/2006" // mm/dd/yyyy date format
	var v string
	d.DecodeElement(&v, &start)
	if v == "N/A" {
		return fmt.Errorf("date not available")
	}
	parse, err := time.Parse(shortForm, v)
	if err != nil {
		return err
	}
	*sT = SimpleTime{parse}
	return nil
}

func NewSimpleTime(day, month, year int) SimpleTime {
	return SimpleTime{time.Date(year, time.Month(month), day, 0, 0, 0, 0, time.UTC)}
}

type _OrgContact struct {
	FirstName string `xml:"FirstName,omitempty"`
	LastName  string `xml:"LastName,omitempty"`
	Phone     string `xml:"Phone,omitempty"`
	Email     string `xml:"Email,omitempty"`
}

type _OrgAddress struct {
	City    string `xml:"City,omitempty"`
	State   string `xml:"State,omitempty"`
	Country string `xml:"Country,omitempty"`
}

type _Organization struct {
	Name        string      `xml:"name,attr,omitempty"`
	OrgStatus   string      `xml:"OrgStatus,omitempty"`
	AuthStatus  string      `xml:"AuthStatus,omitempty"`
	EVEnabled   string      `xml:"EV_Enabled,omitempty"`
	AuthExpires SimpleTime  `xml:"AuthExpires,omitempty"`
	OrgContact  _OrgContact `xml:"OrgContact,omitempty"`
	OrgAddress  _OrgAddress `xml:"OrgAddress,omitempty"`
}

type OrganizationInfo struct {
	ViceResponse

	Organization _Organization `xml:"Organization"`
}

func (c *CertificatesServiceOp) GetOrganizationInfo(ctx context.Context) (*OrganizationInfo, error) {
	req, err := c.client.newRequest(ctx, "GET", getOrgInfoBasePath, nil)
	if err != nil {
		return nil, err
	}

	getOrgInfo := new(OrganizationInfo)
	err = c.client.Do(req, getOrgInfo)
	if err != nil {
		return nil, err
	}

	return getOrgInfo, nil
}
