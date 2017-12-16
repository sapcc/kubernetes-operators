package vice

import (
	"encoding/xml"
	"testing"

	"github.com/stretchr/testify/assert"
)

const getOrgInfoResponse = `
<Response xmlns:tns="http://webservices.mpki4ssl.verisign.com">
<StatusCode>0x00</StatusCode>
<Message>success</Message>
<Organization name="ECorp">
<OrgStatus>Valid</OrgStatus>
<AuthStatus>Authenticated</AuthStatus>
<EV_Enabled>Yes</EV_Enabled>
<AuthExpires>12/13/2018</AuthExpires>
<OrgContact>
<FirstName>Max</FirstName>
<LastName>Cloud</LastName>
<Phone>012345678</Phone>
<Email>max.cloud@gmail.com</Email>
</OrgContact>
<OrgAddress>
<Address>Cloud-Allee 16</Address>
<City>Berlin</City>
<State>Berlin</State>
<Zip>10178</Zip>
<Country>DE</Country>
</OrgAddress>
</Organization>
</Response>
`

func TestGetOrgInfo(t *testing.T) {

	expectedOrgInfo := _Organization{
		Name:        "ECorp",
		OrgStatus:   "Valid",
		AuthStatus:  "Authenticated",
		EVEnabled:   "Yes",
		AuthExpires: NewSimpleTime(13, 12, 2018),
		OrgContact: _OrgContact{
			FirstName: "Max",
			LastName:  "Cloud",
			Phone:     "012345678",
			Email:     "max.cloud@gmail.com",
		},
		OrgAddress: _OrgAddress{
			City:    "Berlin",
			State:   "Berlin",
			Country: "DE",
		},
	}

	var orgInfo OrganizationInfo
	xml.Unmarshal([]byte(getOrgInfoResponse), &orgInfo)

	assert.NotNil(t, orgInfo)
	assert.Equal(t, expectedOrgInfo, orgInfo.Organization)

}
