package disco

import (
	"strings"

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

// addSuffixIfRequired ensures the recordset name ends with '.'
func addSuffixIfRequired(s string) string {
	if !strings.HasSuffix(s, ".") {
		return s + "."
	}
	return s
}

func listDesignateZones(dnsV2Client *gophercloud.ServiceClient, opts zones.ListOpts) (zoneList []zones.Zone, err error) {
	pages := 0
	err = zones.List(dnsV2Client, opts).EachPage(func(page pagination.Page) (bool, error) {
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

func getDesignateZoneByName(dnsV2Client *gophercloud.ServiceClient, zoneName string) (zones.Zone, error) {
	zoneList, err := listDesignateZones(dnsV2Client, zones.ListOpts{Name: addSuffixIfRequired(zoneName)})
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

func listDesignateRecordsetsForZone(dnsV2Client *gophercloud.ServiceClient, zone zones.Zone) (recordsetList []recordsets.RecordSet, err error) {
	pages := 0
	err = recordsets.ListByZone(dnsV2Client, zone.ID, recordsets.ListOpts{}).EachPage(func(page pagination.Page) (bool, error) {
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

func createDesignateRecordset(dnsV2Client *gophercloud.ServiceClient, zoneID, rsName string, records []string, recordsetTTL int, rsType string) error {
	LogInfo("would create recordset name: %s, type: %s, records: %v, ttl: %v in zone %s ", rsName, rsType, records, recordsetTTL, zoneID)
	//TODO:
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
