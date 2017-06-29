package vice

import (
	"context"
)

const approveBasePath = "/vswebservices/rest/services/approve"

type ApprovalRequest struct {
	TransactionID string `url:"transaction_id"`
}

type Approval struct {
	ViceResponse

	Certificate string `xml:"Certificate,omitempty"`
}

func (c *CertificatesServiceOp) Approve(ctx context.Context, r *ApprovalRequest) (*Approval, error) {
	path, err := addOptions(approveBasePath, r)
	if err != nil {
		return nil, err
	}

	req, err := c.client.newRequest(ctx, "GET", path, nil)
	if err != nil {
		return nil, err
	}

	approval := new(Approval)
	err = c.client.Do(req, approval)
	if err != nil {
		return nil, err
	}

	return approval, nil
}
