package vice

import (
	"context"
)

const pickupBasePath = "/vswebservices/rest/services/pickup"

type PickupRequest struct {
	TransactionID string `url:"transaction_id"`
}

type Pickup struct {
	ViceResponse

	Certificate string `xml:"Certificate,omitempty"`
}

func (c *CertificatesServiceOp) Pickup(ctx context.Context, r *PickupRequest) (*Pickup, error) {
	path, err := addOptions(pickupBasePath, r)
	if err != nil {
		return nil, err
	}

	req, err := c.client.newRequest(ctx, "GET", path, nil)
	if err != nil {
		return nil, err
	}

	pickup := new(Pickup)
	err = c.client.Do(req, pickup)
	if err != nil {
		return nil, err
	}

	return pickup, nil
}
