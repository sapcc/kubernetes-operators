/*******************************************************************************
*
* Copyright 2019 SAP SE
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You should have received a copy of the License along with this
* program. If not, you may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
*******************************************************************************/

package disco

import (
	"strings"

	"github.com/gophercloud/gophercloud"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/zones"
	"github.com/gophercloud/gophercloud/pagination"
	"github.com/pkg/errors"
	"github.com/sapcc/kubernetes-operators/disco/pkg/log"
)

// RecordsetType defines the types of recordsets
var RecordsetType = struct {
	CNAME,
	NS,
	SOA,
	A string
}{
	"CNAME",
	"NS",
	"SOA",
	"A",
}

func stringToRecordsetType(recType string) string {
	switch recType {
	case RecordsetType.A:
		return RecordsetType.A
	case RecordsetType.NS:
		return RecordsetType.NS
	case RecordsetType.SOA:
		return RecordsetType.SOA
	case RecordsetType.CNAME:
	default:
		return RecordsetType.CNAME
	}
	return RecordsetType.CNAME
}

// Status ...
var Status = struct {
	ACTIVE string
}{
	"ACTIVE",
}

// DNSV2Client ...
type DNSV2Client struct {
	client      *gophercloud.ServiceClient
	moreHeaders map[string]string
	logger      log.Logger
}

// NewDNSV2ClientFromAuthOpts returns a new dns v2 client using provided auth options or an error
func NewDNSV2ClientFromAuthOpts(authOpts AuthOpts, logger log.Logger) (*DNSV2Client, error) {
	client, err := NewOpenStackDesignateClient(authOpts)
	if err != nil {
		return nil, err
	}

	return &DNSV2Client{
		client: client,
		moreHeaders: map[string]string{
			"X-Auth-All-Projects": "true",
		},
		logger: log.NewLoggerWith(logger, "component", "dnsv2client"),
	}, nil
}

func (c *DNSV2Client) listDesignateZones(listOpts zones.ListOpts) ([]zones.Zone, error) {
	url := c.client.ServiceURL("zones")

	listOptsString, err := listOpts.ToZoneListQuery()
	if err != nil {
		return nil, err
	}
	url += listOptsString

	opts := gophercloud.RequestOpts{
		MoreHeaders: c.moreHeaders,
	}

	var res gophercloud.Result
	var resData struct {
		Zones []zones.Zone `json:"zones"`
	}

	_, res.Err = c.client.Get(url, &res.Body, &opts)
	if err := res.ExtractInto(&resData); err != nil {
		return nil, errors.Wrapf(err, "failed to list zones from %v, options: %#v", url, opts)
	}

	c.logger.LogDebug("list designate zones with filter", "filter", listOptsString, "foundZones", zoneListToString(resData.Zones))
	return resData.Zones, nil
}

func (c *DNSV2Client) getDesignateZoneByName(zoneName string) (zones.Zone, error) {
	// Add trailing `.` if not already present.
	zoneName = addSuffixIfRequired(zoneName)

	zoneList, err := c.listDesignateZones(
		zones.ListOpts{
			Name:   zoneName,
			Status: Status.ACTIVE,
		},
	)
	if err != nil {
		return zones.Zone{}, err
	}

	if len(zoneList) > 1 {
		return zones.Zone{}, errors.Errorf("multiple zones with name %s found", zoneName)
	}
	if len(zoneList) == 0 || zoneList[0].Name != zoneName {
		return zones.Zone{}, errors.Errorf("no zone with name %s found", zoneName)
	}
	return zoneList[0], nil
}

func (c *DNSV2Client) listDesignateRecordsetsForZone(zone zones.Zone, recordsetName string) (recordsetList []recordsets.RecordSet, err error) {
	opts := recordsets.ListOpts{}
	if recordsetName != "" {
		opts.Name = addSuffixIfRequired(recordsetName)
	}

	pager := recordsets.ListByZone(c.client, zone.ID, opts)
	pager.Headers = mergeMaps(c.moreHeaders, pager.Headers)

	pages := 0
	err = pager.EachPage(func(page pagination.Page) (bool, error) {
		pages++
		r, err := recordsets.ExtractRecordSets(page)
		if err != nil {
			return false, err
		}
		recordsetList = r
		return true, nil
	})
	if err != nil {
		return nil, errors.Wrapf(err, "Failed to list recordsets in zone %s.", zone.ID)
	}
	c.logger.LogDebug("list designate recordsets", "zone", zone.Name, "recordsetName", recordsetName, "foundRecords", recordSetListToString(recordsetList))
	return recordsetList, nil
}

func (c *DNSV2Client) createDesignateRecordset(zoneID, rsName string, records []string, rsTTL int, rsType, description string) error {
	url := c.client.ServiceURL("zones", zoneID, "recordsets")
	opts := gophercloud.RequestOpts{
		OkCodes:     []int{201, 202},
		MoreHeaders: c.moreHeaders,
	}

	rec, err := recordsets.CreateOpts{
		Name:        addSuffixIfRequired(rsName),
		Records:     records,
		TTL:         rsTTL,
		Type:        rsType,
		Description: description,
	}.ToRecordSetCreateMap()
	if err != nil {
		return err
	}

	var res gophercloud.Result
	if _, res.Err = c.client.Post(url, &rec, &res.Body, &opts); res.Err != nil {
		return errors.Wrapf(err, "Could not create recordset name: %s, type: %s, records: %v, ttl: %v in zone %s. Error: %#v ", rsName, rsType, records, rsTTL, zoneID)
	}
	c.logger.LogInfo("created recordset", "name", rsName, "type", rsType, "records", strings.Join(records, ","), "ttl", rsTTL, "zoneID", zoneID)
	return nil
}

func (c *DNSV2Client) deleteDesignateRecordset(host, recordsetID, zoneID string) error {
	url := c.client.ServiceURL("zones", zoneID, "recordsets", recordsetID)
	opts := gophercloud.RequestOpts{
		OkCodes:     []int{202},
		MoreHeaders: c.moreHeaders,
	}
	if _, err := c.client.Delete(url, &opts); err != nil {
		return errors.Wrapf(err, "could not delete recordset %s with uid %v in zone uid %v", host, recordsetID, zoneID)
	}
	c.logger.LogInfo("deleted recordset", "host", host, "recordsetID", recordsetID, "zoneID", zoneID)
	return nil
}
