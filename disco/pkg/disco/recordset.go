package disco

import (
	"github.com/gophercloud/gophercloud"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/zones"
	"github.com/gophercloud/gophercloud/pagination"
	"github.com/pkg/errors"
)

// RecordsetType defines the types of recordsets
var RecordsetType = struct {
	CNAME string
}{
	"CNAME",
}

var Status = struct {
	ACTIVE string
}{
	"ACTIVE",
}

// DNSV2Client ...
type DNSV2Client struct {
	client  *gophercloud.ServiceClient
	headers map[string]string
}

// NewDNSV2ClientFromAuthOpts returns a new dns v2 client using provided auth options or an error
func NewDNSV2ClientFromAuthOpts(authOpts AuthOpts) (*DNSV2Client, error) {
	client, err := newOpenStackDesignateClient(authOpts)
	if err != nil {
		return nil, err
	}

	return &DNSV2Client{
		client: client,
	}, nil
}

func (c *DNSV2Client) listDesignateZones(opts zones.ListOpts) (zoneList []zones.Zone, err error) {
	pages := 0
	list := zones.List(c.client, opts)
	err = list.EachPage(func(page pagination.Page) (bool, error) {
		pages++
		z, err := zones.ExtractZones(page)
		if err != nil {
			return false, err
		}
		zoneList = z
		return true, nil
	})
	if err != nil {
		return nil, errors.Wrapf(err, "Failed to list zones with options: %#v", opts)
	}
	return zoneList, nil
}

func (c *DNSV2Client) getDesignateZoneByName(zoneName string) (zones.Zone, error) {
	zoneList, err := c.listDesignateZones(
		zones.ListOpts{
			Name:   addSuffixIfRequired(zoneName),
			Status: Status.ACTIVE,
		},
	)
	if err != nil {
		return zones.Zone{}, err
	}
	if len(zoneList) == 0 {
		return zones.Zone{}, errors.Errorf("No zone with name %s found", zoneName)
	}
	if len(zoneList) > 1 {
		return zones.Zone{}, errors.Errorf("Multiple zones with name %s found", zoneName)
	}
	return zoneList[0], nil
}

func (c *DNSV2Client) listDesignateRecordsetsForZone(zone zones.Zone) (recordsetList []recordsets.RecordSet, err error) {
	pages := 0
	err = recordsets.ListByZone(c.client, zone.ID, recordsets.ListOpts{}).EachPage(func(page pagination.Page) (bool, error) {
		pages++
		r, err := recordsets.ExtractRecordSets(page)
		if err != nil {
			return false, err
		}
		recordsetList = r
		return true, nil
	})
	if err != nil {
		return nil, errors.Wrapf(err, "Failed to list recordsets in zone %s. %s.", zone.ID)
	}
	return recordsetList, nil
}

func (c *DNSV2Client) createDesignateRecordset(zoneID, rsName string, records []string, rsTTL int, rsType string) error {
	LogInfo("would create recordset name: %s, type: %s, records: %v, ttl: %v in zone %s ", rsName, rsType, records, rsTTL, zoneID)
	//TODO: commented while testing
	//rs, err := recordsets.Create(dnsV2Client, zoneID, recordsets.CreateOpts{
	//	Name:    rsName,
	//	Records: records,
	//	TTL:     recordsetTTL,
	//	Type:    rsType,
	//}).Extract()
	//if err != nil {
	//	return errors.Wrapf(err, "Could not create recordset name: %s, type: %s, records: %v, ttl: %v in zone %s. Error: %#v ", rs.Name, rs.Type, rs.Records, rs.TTL, rs.ZoneID)
	//}
	//LogInfo("Created recordset name: %s, type: %s, records: %v, ttl: %v in zone %s ", rs.Name, rs.Type, rs.Records, rs.TTL, rs.ZoneID)
	return nil
}

func (c *DNSV2Client) deleteDesignateRecordset(host, recordsetID, zoneID string) error {
	LogInfo("would delete recordset %s in zone %s ", host, zoneID)

	//TODO: commented while testing
	// return recordsets.Delete(dnsV2Client, zoneID, recordsetID).ExtractErr()

	return nil
}
