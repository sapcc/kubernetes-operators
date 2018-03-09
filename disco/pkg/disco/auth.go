/*******************************************************************************
*
* Copyright 2018 SAP SE
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
	"github.com/gophercloud/gophercloud"
	"github.com/gophercloud/gophercloud/openstack"
	"github.com/gophercloud/gophercloud/openstack/identity/v3/tokens"
	"github.com/pkg/errors"
)

// AuthOpts ...
type AuthOpts struct {
	AuthURL           string `yaml:"auth_url"`
	RegionName        string `yaml:"region_name"`
	Username          string `yaml:"username"`
	UserDomainName    string `yaml:"user_domain_name"`
	Password          string `yaml:"password"`
	ProjectName       string `yaml:"project_name"`
	ProjectDomainName string `yaml:"project_domain_name"`
	token             string `yaml:"-"`
}

func newOpenStackServiceClient(authURL string) (*gophercloud.ServiceClient, error) {
	provider, err := openstack.NewClient(authURL)
	if err != nil {
		return nil, errors.Wrap(err, "could not initialize openstack client: %v")
	}
	return &gophercloud.ServiceClient{
		ProviderClient: provider,
		Endpoint:       authURL,
	}, nil

}

func getToken(ao AuthOpts) (string, error) {
	opts := &tokens.AuthOptions{
		IdentityEndpoint: ao.AuthURL,
		Username:         ao.Username,
		Password:         ao.Password,
		DomainName:       ao.UserDomainName,
		AllowReauth:      true,
		Scope: tokens.Scope{
			ProjectName: ao.ProjectName,
			DomainName:  ao.ProjectDomainName,
		},
	}

	client, err := newOpenStackServiceClient(
		ao.AuthURL,
	)
	if err != nil {
		return "", err
	}

	token, err := tokens.Create(client, opts).ExtractToken()
	if err != nil {
		return "", err
	}

	return token.ID, nil
}

func newOpenStackDesignateClient(ao AuthOpts) (*gophercloud.ServiceClient, error) {
	if ao.token == "" {
		return nil, errors.New("no token obtained. authentication required")
	}

	provider, err := openstack.AuthenticatedClient(
		gophercloud.AuthOptions{
			IdentityEndpoint: ao.AuthURL,
			TokenID:          ao.token,
		},
	)
	if err != nil {
		return nil, errors.New("unable to create designate client with given token")
	}

	return openstack.NewDNSV2(
		provider,
		gophercloud.EndpointOpts{Availability: gophercloud.AvailabilityPublic},
	)
}
