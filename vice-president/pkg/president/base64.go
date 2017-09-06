package president

import (
	"encoding/base64"
	"fmt"
)

func base64EncodePEM(pem []byte) ([]byte, error) {
	base64EncodedPEM := make([]byte, base64.StdEncoding.EncodedLen(len(pem)))
	base64.StdEncoding.Encode(base64EncodedPEM, pem)
	if base64EncodedPEM == nil {
		return nil, fmt.Errorf("Couldn't base64-encode PEM %#v", string(pem))
	}
	return base64EncodedPEM, nil
}

func base64DecodePEM(encodedPEM []byte) ([]byte, int, error) {
	decodedPEM := make([]byte, base64.StdEncoding.DecodedLen(len(encodedPEM)))
	l, err := base64.StdEncoding.Decode(decodedPEM, encodedPEM)
	if err != nil {
		return nil, 0, err
	}
	return decodedPEM, l, nil
}
