package vice

import (
	"encoding/xml"
	"testing"

	"github.com/stretchr/testify/assert"
)

const getTokenCountResponse = `
<Response xmlns:tns="urn:symantec:api">
<StatusCode>0x00</StatusCode>
<Message>success</Message>
<TokenCount type="Server" ordered="1000" used="969" remaining="31"></TokenCount>
<TokenCount type="GlobalServer" ordered="100" used="20" remaining="80"></TokenCount>
<TokenCount type="IntranetServer" ordered="1" used="1" remaining="99"></TokenCount>
<TokenCount type="IntranetGlobalServer" ordered="3" used="2" remaining="1"></TokenCount>
<TokenCount type="OFXServer" ordered="10" used="5" remaining="90"></TokenCount>
</Response>
`

func TestGetToken(t *testing.T) {

	expectedTokenCount := map[_CertProductType]map[string]int{
		CertProductType.Server:               {"ordered": 1000, "used": 969, "remaining": 31},
		CertProductType.GlobalServer:         {"ordered": 100, "used": 20, "remaining": 80},
		CertProductType.IntranetServer:       {"ordered": 1, "used": 1, "remaining": 99},
		CertProductType.IntranetGlobalServer: {"ordered": 3, "used": 2, "remaining": 1},
		CertProductType.OFXServer:            {"ordered": 10, "used": 5, "remaining": 90},
	}

	var tokenCount TokenCount
	xml.Unmarshal([]byte(getTokenCountResponse), &tokenCount)

	assert.NotNil(t, tokenCount)
	assert.NotEmpty(t, tokenCount.Tokens)

	for _, item := range tokenCount.Tokens {
		assert.NotNil(t, item)
		expected, ok := expectedTokenCount[item.Type]
		if !ok {
			t.Errorf("unknown item %v", item)
		}
		assert.Equal(t, expected["ordered"], item.Ordered)
		assert.Equal(t, expected["used"], item.Used)
		assert.Equal(t, expected["remaining"], item.Remaining)
	}
}
