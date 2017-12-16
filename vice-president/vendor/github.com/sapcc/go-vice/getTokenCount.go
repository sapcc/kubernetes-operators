package vice

import (
	"context"
	"encoding/xml"
)

const getTokenCountsBasePath = "/vswebservices/rest/services/gettokencounts"

type _TokenCount struct {
	xmlName   xml.Name         `xml:"TokenCount"`
	Type      _CertProductType `xml:"type,attr,omitempty"`
	Ordered   int              `xml:"ordered,attr,omitempty"`
	Used      int              `xml:"used,attr,omitempty"`
	Remaining int              `xml:"remaining,attr,omitempty"`
}

type TokenCount struct {
	ViceResponse
	Tokens []_TokenCount `xml:"TokenCount"`
}

func (c *CertificatesServiceOp) GetTokenCount(ctx context.Context) (*TokenCount, error) {
	req, err := c.client.newRequest(ctx, "GET", getTokenCountsBasePath, nil)
	if err != nil {
		return nil, err
	}

	getToken := new(TokenCount)
	err = c.client.Do(req, getToken)
	if err != nil {
		return nil, err
	}

	return getToken, nil
}
