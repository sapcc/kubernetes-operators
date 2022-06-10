/*
Copyright 2022 SAP SE.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package disco

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/gophercloud/gophercloud"
	"github.com/gophercloud/gophercloud/openstack"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/recordsets"
	"github.com/gophercloud/gophercloud/openstack/dns/v2/zones"
	"github.com/gophercloud/gophercloud/openstack/identity/v3/tokens"
	"github.com/gophercloud/gophercloud/pagination"
	"github.com/pkg/errors"
	utilerrors "k8s.io/apimachinery/pkg/util/errors"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

var headersForAllDesignateRequests = map[string]string{
	"X-Auth-All-Projects": "true",
}

// DNSV2Client ...
type DNSV2Client struct {
	client *gophercloud.ServiceClient
}

func NewDNSV2ClientFromENV() (*DNSV2Client, error) {
	opts := &tokens.AuthOptions{
		IdentityEndpoint: os.Getenv("OS_AUTH_URL"),
		Username:         os.Getenv("OS_USERNAME"),
		Password:         os.Getenv("OS_PASSWORD"),
		DomainName:       os.Getenv("OS_DOMAIN_NAME"),
		AllowReauth:      true,
		Scope: tokens.Scope{
			ProjectName: os.Getenv("OS_PROJECT_NAME"),
			DomainName:  os.Getenv("OS_PROJECT_DOMAIN_NAME"),
		},
	}
	provider, err := openstack.NewClient(opts.IdentityEndpoint)
	if err != nil {
		return nil, errors.Wrapf(err, "could not initialize openstack client")
	}
	provider.UseTokenLock()

	if err := openstack.AuthenticateV3(provider, opts, gophercloud.EndpointOpts{}); err != nil {
		return nil, errors.Wrap(err, "openstack authentication failed")
	}
	if provider.TokenID == "" {
		return nil, errors.New("token is empty. openstack authentication failed")
	}
	c, err := openstack.NewDNSV2(
		provider,
		gophercloud.EndpointOpts{Region: os.Getenv("OS_REGION_NAME"), Availability: gophercloud.AvailabilityPublic},
	)
	for k, v := range headersForAllDesignateRequests {
		c.MoreHeaders[k] = v
	}
	return &DNSV2Client{client: c}, nil
}

func (c *DNSV2Client) GetZoneByName(ctx context.Context, zoneName string) (zones.Zone, error) {
	zoneName = ensureFQDN(zoneName)
	zoneList, err := c.listZones(ctx, zones.ListOpts{Name: zoneName})
	if err != nil {
		return zones.Zone{}, err
	}
	for _, zone := range zoneList {
		if zone.Name == zoneName {
			return zone, nil
		}
	}
	return zones.Zone{}, fmt.Errorf("no zone with name found: %s", zoneName)
}

func (c *DNSV2Client) GetRecordsetByZoneAndName(ctx context.Context, zoneID, recordsetName string) (recordsets.RecordSet, bool, error) {
	recordsetList, err := c.listRecordsets(ctx, zoneID, recordsetName)
	if err != nil {
		return recordsets.RecordSet{}, false, err
	}
	switch len(recordsetList) {
	case 0:
		return recordsets.RecordSet{}, false, nil
	case 1:
		return recordsetList[0], true, nil
	default:
		return recordsets.RecordSet{}, true, fmt.Errorf("multiple recordsset found in zone %s, name %s", zoneID, recordsetName)
	}
}

func (c *DNSV2Client) CreateRecordset(ctx context.Context, zoneID, name, rsType, description string, records []string, recordsetTTL int) error {
	log.FromContext(ctx).V(5).Info("creating recordset",
		"zoneID", zoneID, "name", name, "type", rsType, "records", strings.Join(records, ","))
	_, err := recordsets.Create(c.client, zoneID, recordsets.CreateOpts{
		Name:        ensureFQDN(name),
		Description: description,
		Records:     records,
		TTL:         recordsetTTL,
		Type:        rsType,
	}).Extract()
	return err
}

func (c *DNSV2Client) DeleteRecordsetByZoneAndNameIgnoreNotFound(ctx context.Context, zoneID, recordsetName string) error {
	recordsetList, err := c.listRecordsets(ctx, zoneID, recordsetName)
	if err != nil {
		return err
	}
	allErrs := make([]error, 0)
	for _, record := range recordsetList {
		log.FromContext(ctx).Info("deleting record",
			"zone", record.ZoneName, "name", record.Name, "type", record.Type, "id", record.ID)
		if err := c.deleteRecordsetIgnoreNotFound(ctx, zoneID, record.ID).ExtractErr(); err != nil {
			allErrs = append(allErrs, err)
		}
	}
	if len(allErrs) > 0 {
		return utilerrors.NewAggregate(allErrs)
	}
	return nil
}

func (c *DNSV2Client) deleteRecordsetIgnoreNotFound(_ context.Context, zoneID string, rrsetID string) (r recordsets.DeleteResult) {
	resp, err := c.client.Delete(c.client.ServiceURL("zones", zoneID, "recordsets", rrsetID), &gophercloud.RequestOpts{
		OkCodes: []int{202, 404},
	})
	_, r.Header, r.Err = gophercloud.ParseResponse(resp, err)
	return
}

func (c *DNSV2Client) UpdateRecordset(zoneID, recordsetID, description string, recordsetTTL int, records []string) error {
	_, err := recordsets.Update(c.client, zoneID, recordsetID, recordsets.UpdateOpts{
		Description: &description,
		TTL:         &recordsetTTL,
		Records:     records,
	}).Extract()
	return err
}

func (c *DNSV2Client) listZones(ctx context.Context, listOpts zones.ListOpts) ([]zones.Zone, error) {
	log.FromContext(ctx).V(5).Info("listing zones", "listOpts", listOpts)
	zoneList := make([]zones.Zone, 0)
	pager := zones.List(c.client, listOpts)
	if err := pager.EachPage(func(page pagination.Page) (bool, error) {
		zonesPerPage, err := zones.ExtractZones(page)
		if err != nil {
			return false, err
		}
		zoneList = append(zoneList, zonesPerPage...)
		return true, nil
	}); err != nil {
		return nil, err
	}
	return zoneList, nil
}

func (c *DNSV2Client) listRecordsets(ctx context.Context, zoneID, recordsetName string) ([]recordsets.RecordSet, error) {
	log.FromContext(ctx).V(5).Info("listing recordsets", "zoneID", zoneID, "name", recordsetName)
	recordsetList := make([]recordsets.RecordSet, 0)
	pager := recordsets.ListByZone(c.client, zoneID, recordsets.ListOpts{ZoneID: zoneID, Name: recordsetName})
	if err := pager.EachPage(func(page pagination.Page) (bool, error) {
		recordsetsPerPage, err := recordsets.ExtractRecordSets(page)
		if err != nil {
			return false, err
		}
		recordsetList = append(recordsetList, recordsetsPerPage...)
		return true, nil
	}); err != nil {
		return nil, err
	}
	return recordsetList, nil
}
