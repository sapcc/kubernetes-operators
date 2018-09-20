// Copyright 2017 SAP SE
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package v1

import (
	"errors"
	"fmt"
	"regexp"

	"github.com/golang/glog"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	utils "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder"
)

const OpenstackSeedResourcePlural = "openstackseeds"

// The top level openstack seed element.
//
// It can have dependencies (that define elements that are refered to in the seed) that will be resolved before seeding the specs content.

type OpenstackSeed struct {
	metav1.TypeMeta     `json:",inline"`
	metav1.ObjectMeta   `json:"metadata"`
	Spec                OpenstackSeedSpec `json:"spec" yaml:"spec"`
	VisitedDependencies map[string]bool
}

type OpenstackSeedList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`

	Items []OpenstackSeed `json:"items" yaml:"items"`
}

//
// Cross kubernetes namespace dependencies can be defined by using a fully qualified **requires** notation that includes a namespace: namespace/specname
type OpenstackSeedSpec struct {
	Dependencies    []string      `json:"requires,omitempty" yaml:"requires,omitempty"`                 // list of required specs that need to be resolved before the current one
	Roles           []string      `json:"roles,omitempty" yaml:"roles,omitempty"`                       // list of keystone roles
	ResourceClasses []string      `json:"resource_classes,omitempty" yaml:"resource_classes,omitempty"` // list of resource classes for the placement service (currently still part of nova)
	Regions         []RegionSpec  `json:"regions,omitempty" yaml:"regions,omitempty"`                   // list keystone regions
	Services        []ServiceSpec `json:"services,omitempty" yaml:"services,omitempty"`                 // list keystone services and their endpoints
	Flavors         []FlavorSpec  `json:"flavors,omitempty" yaml:"flavors,omitempty"`                   // list of nova flavors
	Domains         []DomainSpec  `json:"domains,omitempty" yaml:"domains,omitempty"`                   // list keystone domains with their configuration, users, groups, projects, etc.
}

// A keystone region (see https://developer.openstack.org/api-ref/identity/v3/index.html#regions)
type RegionSpec struct {
	Region       string `json:"id" yaml:"id"`                                           // the region id
	Description  string `json:"description,omitempty" yaml:"description,omitempty"`     // the regions description
	ParentRegion string `json:"parent_region,omitempty" yaml:"parent_region,omitempty"` // the (optional) id of the parent region
}

// A keystone service (see https://developer.openstack.org/api-ref/identity/v3/index.html#service-catalog-and-endpoints)
type ServiceSpec struct {
	Name        string         `json:"name" yaml:"name"`                                   // service name
	Type        string         `json:"type" yaml:"type"`                                   // service type
	Description string         `json:"description,omitempty" yaml:"description,omitempty"` // description of the service
	Enabled     *bool          `json:"enabled,omitempty" yaml:"enabled,omitempty"`         // boolean flag to indicate if the service is enabled
	Endpoints   []EndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`     // list of service endpoints
}

// A keystone service endpoint (see https://developer.openstack.org/api-ref/identity/v3/index.html#service-catalog-and-endpoints)
type EndpointSpec struct {
	Region    string `json:"region" yaml:"region"`                       // region-id
	Interface string `json:"interface" yaml:"interface"`                 // interface type (usually public, admin, internal)
	URL       string `json:"url" yaml:"url"`                             // the endpoints URL
	Enabled   *bool  `json:"enabled,omitempty" yaml:"enabled,omitempty"` // boolean flag to indicate if the endpoint is enabled
}

// A keystone domain (see https://developer.openstack.org/api-ref/identity/v3/index.html#domains)
type DomainSpec struct {
	Name            string               `json:"name" yaml:"name"`                                   // domain name
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"` // domain description
	Enabled         *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`         // boolean flag to indicate if the domain is enabled
	Users           []UserSpec           `json:"users,omitempty" yaml:"users,omitempty"`             // list of domain users
	Groups          []GroupSpec          `json:"groups,omitempty" yaml:"groups,omitempty"`           // list of domain groups
	Projects        []ProjectSpec        `json:"projects,omitempty" yaml:"projects,omitempty"`       // list of domain projects
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of domain-role-assignments
	Config          DomainConfigSpec     `json:"config,omitempty" yaml:"config,omitempty"`           // optional domain configuration
}

// A keystone domain configuation (see https://developer.openstack.org/api-ref/identity/v3/index.html#domain-configuration)
//
// The cc_ad configuration element refers to the SAP Converged Cloud customer driver extensions
type DomainConfigSpec struct {
	IdentityConfig map[string]string      `json:"identity,omitempty" yaml:"identity,omitempty"` // the identity driver configuration settings
	LdapConfig     map[string]interface{} `json:"ldap,omitempty" yaml:"ldap,omitempty"`         // the ldap driver configuration settings
	CCAdConfig     map[string]interface{} `json:"cc_ad,omitempty" yaml:"cc_ad,omitempty"`       // the cc_ad driver configuration settings
}

// A keystone project (see https://developer.openstack.org/api-ref/identity/v3/index.html#projects)
type ProjectSpec struct {
	Name            string                `json:"name" yaml:"name"`                                         // project name
	Description     string                `json:"description,omitempty" yaml:"description,omitempty"`       // project description
	Enabled         *bool                 `json:"enabled,omitempty" yaml:"enabled,omitempty"`               // boolean flag to indicate if the project is enabled
	Parent          string                `json:"parent,omitempty" yaml:"parent,omitempty"`                 // (optional) parent project id
	IsDomain        *bool                 `json:"is_domain,omitempty" yaml:"is_domain,omitempty"`           // is the project actually a domain?
	Endpoints       []ProjectEndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`           // list of project endpoint filters
	RoleAssignments []RoleAssignmentSpec  `json:"roles,omitempty" yaml:"roles,omitempty"`                   // list of project-role-assignments
	Flavors         []string              `json:"flavors,omitempty" yaml:"flavors,omitempty"`               // list of nova flavor-id's
	AddressScopes   []AddressScopeSpec    `json:"address_scopes,omitempty" yaml:"address_scopes,omitempty"` // list of neutron address-scopes
	SubnetPools     []SubnetPoolSpec      `json:"subnet_pools,omitempty" yaml:"subnet_pools,omitempty"`     // list of neutron subnet-pools
	NetworkQuota    *NetworkQuotaSpec     `json:"network_quota,omitempty" yaml:"network_quota,omitempty"`   // neutron quota
	Networks        []NetworkSpec         `json:"networks,omitempty" yaml:"networks,omitempty"`             // neutron networks
	Routers         []RouterSpec          `json:"routers,omitempty" yaml:"routers,omitempty"`               // neutron routers
	Swift           *SwiftAccountSpec     `json:"swift,omitempty" yaml:"swift,omitempty"`                   // swift account
	DNSQuota        *DNSQuotaSpec         `json:"dns_quota,omitempty" yaml:"dns_quota,omitempty"`           // designate quota
	DNSZones        []DNSZoneSpec         `json:"dns_zones,omitempty" yaml:"dns_zones,omitempty"`           // designate zones, recordsets
	DNSTSIGKeys     []DNSTSIGKeySpec      `json:"dns_tsigkeys,omitempty" yaml:"dns_tsigkeys,omitempty"`     // designate tsig keys
}

// A project endpoint filter (see https://developer.openstack.org/api-ref/identity/v3-ext/#os-ep-filter-api)
type ProjectEndpointSpec struct {
	Region  string `json:"region" yaml:"region"`   // region-id
	Service string `json:"service" yaml:"service"` // service-id
}

// A keystone role assignment (see https://developer.openstack.org/api-ref/identity/v3/#roles).
//
// Role assignments can be assigned to users, groups, domain and projects.
//
// A role assignment always links 3 entities: user or group to project or domain with a specified role.
//
// To support cross domain entity referals, the user-, group- or project-names support a name@domain notation.
type RoleAssignmentSpec struct {
	Role      string `json:"role" yaml:"role"`                                 // the role name
	Domain    string `json:"domain,omitempty" yaml:"domain,omitempty"`         // domain-role-assigment: the domain name
	Project   string `json:"project,omitempty" yaml:"project,omitempty"`       // project-role-assignment: project_name@domain_name
	ProjectID string `json:"project_id,omitempty" yaml:"project_id,omitempty"` // project-role assignment: project id
	Group     string `json:"group,omitempty" yaml:"group,omitempty"`           // group name (for project/domain group-role-assignment)
	User      string `json:"user,omitempty" yaml:"user,omitempty"`             // user name (for project/domain user-role-assignment)
	Inherited *bool  `json:"inherited,omitempty" yaml:"inherited,omitempty"`   // boolean flag to indicate if the role-assignment should be inherited
}

// A keystone user (see https://developer.openstack.org/api-ref/identity/v3/#users)
type UserSpec struct {
	Name             string               `json:"name" yaml:"name"`                                           // username
	Description      string               `json:"description,omitempty" yaml:"description,omitempty"`         // description of the user
	Password         string               `json:"password,omitempty" yaml:"password,omitempty"`               // password of the user (only evaluated on user creation)
	Enabled          *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`                 // boolean flag to indicate if the user is enabled
	RoleAssignments  []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`                     // list of the users role-assignments
	DefaultProjectID string               `json:"default_project,omitempty" yaml:"default_project,omitempty"` // default project scope for the user
}

// A keystone group (see https://developer.openstack.org/api-ref/identity/v3/#groups)
type GroupSpec struct {
	Name            string               `json:"name" yaml:"name"`                                   // group name
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"` // description of the group
	Users           []string             `json:"users,omitempty" yaml:"users,omitempty"`             // a list of group members (user names)
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of the groups role-assignments
}

// A nova flavor (see https://developer.openstack.org/api-ref/compute/#flavors)
type FlavorSpec struct {
	Name       string                 `json:"name" yaml:"name"` // flavor name
	Id         string                 `json:"id,omitempty" yaml:"id,omitempty"`
	Ram        int                    `json:"ram,omitempty" yaml:"ram,omitempty"`
	Disk       int                    `json:"disk,omitempty" yaml:"disk,omitempty"`
	Vcpus      int                    `json:"vcpus,omitempty" yaml:"vcpus,omitempty"`
	Swap       int                    `json:"swap,omitempty" yaml:"swap,omitempty"`
	RxTxfactor float32                `json:"rxtxfactor,omitempty" yaml:"rxtxfactor,omitempty"`
	IsPublic   *bool                  `json:"is_public,omitempty" yaml:"is_public,omitempty"`
	Disabled   *bool                  `json:"disabled,omitempty" yaml:"disabled,omitempty"`
	Ephemeral  int                    `json:"ephemeral,omitempty" yaml:"ephemeral,omitempty"`
	ExtraSpecs map[string]interface{} `json:"extra_specs,omitempty" yaml:"extra_specs,omitempty"` // list of extra specs
}

// A neutron address scope (see https://developer.openstack.org/api-ref/networking/v2/index.html  UNDOCUMENTED)
type AddressScopeSpec struct {
	Name        string           `json:"name" yaml:"name"`                                     // address scope name
	IpVersion   int              `json:"ip_version" yaml:"ip_version"`                         // ip-version 4 or 6
	Shared      *bool            `json:"shared,omitempty" yaml:"shared,omitempty"`             // boolean flag to indicate if the address-scope is shared
	SubnetPools []SubnetPoolSpec `json:"subnet_pools,omitempty" yaml:"subnet_pools,omitempty"` // list of subnet-pools in the address-scope
}

// A neutron subnet pool (see https://developer.openstack.org/api-ref/networking/v2/index.html#subnet-pools)
type SubnetPoolSpec struct {
	Name             string   `json:"name" yaml:"name"`                                               // subnet-pool name
	DefaultQuota     int      `json:"default_quota,omitempty" yaml:"default_quota,omitempty"`         // A per-project quota on the prefix space that can be allocated from the subnet pool for project subnets.
	Prefixes         []string `json:"prefixes" yaml:"prefixes"`                                       // A list of subnet prefixes to assign to the subnet pool
	MinPrefixLen     int      `json:"min_prefixlen,omitempty" yaml:"min_prefixlen,omitempty"`         // The smallest prefix that can be allocated from a subnet pool.
	Shared           *bool    `json:"shared,omitempty" yaml:"shared,omitempty"`                       // Admin-only. Indicates whether this network is shared across all projects.
	DefaultPrefixLen int      `json:"default_prefixlen,omitempty" yaml:"default_prefixlen,omitempty"` // The size of the prefix to allocate when the cidr or prefixlen attributes are omitted when you create the subnet. Default is min_prefixlen.
	MaxPrefixLen     int      `json:"max_prefixlen,omitempty" yaml:"max_prefixlen,omitempty"`         // The maximum prefix size that can be allocated from the subnet pool. For IPv4 subnet pools, default is 32. For IPv6 subnet pools, default is 128.
	AddressScopeId   string   `json:"address_scope_id,omitempty" yaml:"address_scope_id,omitempty"`   // An address scope to assign to the subnet pool.
	IsDefault        *bool    `json:"is_default,omitempty" yaml:"is_default,omitempty"`
	Description      string   `json:"description,omitempty" yaml:"description,omitempty"` // description of the subnet-pool
}

// A neutron project quota (see https://developer.openstack.org/api-ref/networking/v2/index.html#quotas-extension-quotas)
type NetworkQuotaSpec struct {
	FloatingIP        int `json:"floatingip,omitempty" yaml:"floatingip,omitempty"`                   // The number of floating IP addresses allowed for each project. A value of -1 means no limit.
	Network           int `json:"network,omitempty" yaml:"network,omitempty"`                         // The number of networks allowed for each project. A value of -1 means no limit.
	Port              int `json:"port,omitempty" yaml:"port,omitempty"`                               // The number of ports allowed for each project. A value of -1 means no limit.
	RbacPolicy        int `json:"rbac_policy,omitempty" yaml:"rbac_policy,omitempty"`                 // The number of role-based access control (RBAC) policies for each project. A value of -1 means no limit.
	Router            int `json:"router,omitempty" yaml:"router,omitempty"`                           // The number of routers allowed for each project. A value of -1 means no limit.
	SecurityGroup     int `json:"security_group,omitempty" yaml:"security_group,omitempty"`           // The number of security groups allowed for each project. A value of -1 means no limit.
	SecurityGroupRule int `json:"security_group_rule,omitempty" yaml:"security_group_rule,omitempty"` // The number of security group rules allowed for each project. A value of -1 means no limit.
	Subnet            int `json:"subnet,omitempty" yaml:"subnet,omitempty"`                           // The number of subnets allowed for each project. A value of -1 means no limit.
	SubnetPool        int `json:"subnetpool,omitempty" yaml:"subnetpool,omitempty"`                   // The number of subnet pools allowed for each project. A value of -1 means no limit.
	HealthMonitor     int `json:"healthmonitor,omitempty" yaml:"healthmonitor,omitempty"`             //
	L7Policy          int `json:"l7policy,omitempty" yaml:"l7policy,omitempty"`                       //
	Listener          int `json:"listener,omitempty" yaml:"listener,omitempty"`                       //
	LoadBalancer      int `json:"loadbalancer,omitempty" yaml:"loadbalancer,omitempty"`               //
}

// A neutron network (see https://developer.openstack.org/api-ref/networking/v2/index.html#networks)
type NetworkSpec struct {
	Name                    string       `json:"name" yaml:"name"`                                                               // network name
	AdminStateUp            *bool        `json:"admin_state_up,omitempty" yaml:"admin_state_up,omitempty"`                       // The administrative state of the network, which is up (true) or down (false).
	PortSecurityEnabled     *bool        `json:"port_security_enabled,omitempty" yaml:"port_security_enabled,omitempty"`         // The port security status of the network. Valid values are enabled (true) and disabled (false). This value is used as the default value of port_security_enabled field of a newly created port.
	ProviderNetworkType     string       `json:"provider_network_type,omitempty" yaml:"provider_network_type,omitempty"`         // The type of physical network that this network should be mapped to. For example, flat, vlan, vxlan, or gre. Valid values depend on a networking back-end.
	ProviderPhysicalNetwork string       `json:"provider_physical_network,omitempty" yaml:"provider_physical_network,omitempty"` // The physical network where this network should be implemented. The Networking API v2.0 does not provide a way to list available physical networks. For example, the Open vSwitch plug-in configuration file defines a symbolic name that maps to specific bridges on each compute host.
	ProviderSegmentationId  string       `json:"provider_segmentation_id,omitempty" yaml:"provider_segmentation_id,omitempty"`   // The ID of the isolated segment on the physical network. The network_type attribute defines the segmentation model. For example, if the network_type value is vlan, this ID is a vlan identifier. If the network_type value is gre, this ID is a gre key.
	QosPolicyId             string       `json:"qos_policy_id,omitempty" yaml:"qos_policy_id,omitempty"`                         // The ID of the QoS policy.
	RouterExternal          *bool        `json:"router_external,omitempty" yaml:"router_external,omitempty"`                     // Indicates whether this network can provide floating IPs via a router.
	Shared                  *bool        `json:"shared,omitempty" yaml:"shared,omitempty"`                                       // Indicates whether this network is shared across all projects. By default, only administrative users can change this value.
	VlanTransparent         *bool        `json:"vlan_transparent,omitempty" yaml:"vlan_transparent,omitempty"`                   // Indicates the VLAN transparency mode of the network, which is VLAN transparent (true) or not VLAN transparent (false).
	Description             string       `json:"description,omitempty" yaml:"description,omitempty"`                             // description of the network
	Subnets                 []SubnetSpec `json:"subnets,omitempty" yaml:"subnets,omitempty"`                                     // List of subnets
	Tags                    []string     `json:"tags,omitempty" yaml:"tags,omitempty"`                                           // List of network tags (see https://developer.openstack.org/api-ref/networking/v2/index.html#tag-extension-tags)
}

// A neutron subnet (see https://developer.openstack.org/api-ref/networking/v2/index.html#subnets)
type SubnetSpec struct {
	Name            string   `json:"name" yaml:"name"`                                               // network name
	EnableDHCP      *bool    `json:"enable_dhcp,omitempty" yaml:"enable_dhcp,omitempty"`             // Indicates whether dhcp is enabled or disabled for the subnet. Default is true.
	DNSNameServers  []string `json:"dns_name_servers,omitempty" yaml:"dns_name_servers,omitempty"`   // List of dns name servers associated with the subnet.
	AllocationPools []string `json:"allocation_pools,omitempty" yaml:"allocation_pools,omitempty"`   // Allocation pools with start and end IP addresses for this subnet. If allocation_pools are not specified, OpenStack Networking automatically allocates pools for covering all IP addresses in the CIDR, excluding the address reserved for the subnet gateway by default.
	HostRoutes      []string `json:"host_routes,omitempty" yaml:"host_routes,omitempty"`             // Additional routes for the subnet. A list of dictionaries with destination and nexthop parameters.
	IpVersion       int      `json:"ip_version,omitempty" yaml:"ip_version,omitempty"`               // ip-version 4 or 6
	GatewayIP       string   `json:"gateway_ip,omitempty" yaml:"gateway_ip,omitempty"`               // Gateway IP of this subnet. If the value is null that implies no gateway is associated with the subnet. If the gateway_ip is not specified, OpenStack Networking allocates an address from the CIDR for the gateway for the subnet by default.
	CIDR            string   `json:"cidr,omitempty" yaml:"cidr,omitempty"`                           // The CIDR of the subnet.
	Description     string   `json:"description,omitempty" yaml:"description,omitempty"`             // description of the network
	Prefixlen       *int     `json:"prefixlen,omitempty" yaml:"prefixlen,omitempty"`                 // The prefix length to use for subnet allocation from a subnet pool. If not specified, the default_prefixlen value of the subnet pool will be used.
	IPV6AddressMode string   `json:"ipv6_address_mode,omitempty" yaml:"ipv6_address_mode,omitempty"` // The IPv6 address modes specifies mechanisms for assigning IP addresses. Value is slaac, dhcpv6-stateful, dhcpv6-stateless.
	IPV6RaMode      string   `json:"ipv6_ra_mode,omitempty" yaml:"ipv6_ra_mode,omitempty"`           // The IPv6 router advertisement specifies whether the networking service should transmit ICMPv6 packets, for a subnet. Value is slaac, dhcpv6-stateful, dhcpv6-stateless.
	SegmentlId      string   `json:"segment_id,omitempty" yaml:"segment_id,omitempty"`               // The ID of a network segment the subnet is associated with. It is available when segment extension is enabled.
	SubnetPoolId    string   `json:"subnetpool_id,omitempty" yaml:"subnetpool_id,omitempty"`         // Subnet-pool ID
	SubnetPool      string   `json:"subnetpool,omitempty" yaml:"subnetpool,omitempty"`               // Subnet-pool name within teh subnets project
	Tags            []string `json:"tags,omitempty" yaml:"tags,omitempty"`                           // List of subnet tags (see https://developer.openstack.org/api-ref/networking/v2/index.html#tag-extension-tags)
}

// A neutron router (see https://developer.openstack.org/api-ref/networking/v2/index.html#routers)
type RouterSpec struct {
	Name                string                   `json:"name" yaml:"name"`                                         // router name
	AdminStateUp        *bool                    `json:"admin_state_up,omitempty" yaml:"admin_state_up,omitempty"` // The administrative state of the router, which is up (true) or down (false).
	Description         string                   `json:"description,omitempty" yaml:"description,omitempty"`       // description of the router
	ExternalGatewayInfo *ExternalGatewayInfoSpec `json:"external_gateway_info,omitempty" yaml:"external_gateway_info,omitempty"`
	Distributed         *bool                    `json:"distributed,omitempty" yaml:"distributed,omitempty"`         // true indicates a distributed router. It is available when dvr extension is enabled.
	HA                  *bool                    `json:"ha,omitempty" yaml:"ha,omitempty"`                           // true indicates a highly-available router. It is available when l3-ha extension is enabled.
	FlavorId            string                   `json:"flavor_id,omitempty" yaml:"flavor_id,omitempty"`             // The ID of the flavor associated with the router
	ServiceTypeId       string                   `json:"service_type_id,omitempty" yaml:"service_type_id,omitempty"` // The ID of the service type associated with the router.
	RouterPorts         []RouterPortSpec         `json:"interfaces,omitempty" yaml:"interfaces,omitempty"`           // Router internal interface specs. This means a specified subnet is attached to a router as an internal router interface.
	Routes              []RouterRouteSpec        `json:"routes,omitempty" yaml:"routes,omitempty"`                   // The extra routes configuration for L3 router. It is available when extraroute extension is enabled.
}

type ExternalGatewayInfoSpec struct {
	Network          string                 `json:"network,omitempty" yaml:"network,omitempty"`                       // network-name (network@project@domain)
	NetworkId        string                 `json:"network_id,omitempty" yaml:"network_id,omitempty"`                 // or network-id
	EnableSNAT       *bool                  `json:"enable_snat,omitempty" yaml:"enable_snat,omitempty"`               // Enable Source NAT (SNAT) attribute. Default is true. To persist this attribute value, set the enable_snat_by_default option in the neutron.conf file. It is available when ext-gw-mode extension is enabled.
	ExternalFixedIPs []ExternalFixedIPsSpec `json:"external_fixed_ips,omitempty" yaml:"external_fixed_ips,omitempty"` // external gateway interface of the router. It is a list of IP addresses you would like to assign to the external gateway interface.
}

type ExternalFixedIPsSpec struct {
	Subnet    string `json:"subnet,omitempty" yaml:"subnet,omitempty"`         // subnet-name (subnet@project@domain)
	SubnetId  string `json:"subnet_id,omitempty" yaml:"subnet_id,omitempty"`   // or subnet-id
	IpAddress string `json:"ip_address,omitempty" yaml:"ip_address,omitempty"` // IP address
}

type RouterPortSpec struct {
	PortId   string `json:"port_id,omitempty" yaml:"port_id,omitempty"`     // The ID of the port. One of subnet_id or port_id must be specified.
	Subnet   string `json:"subnet,omitempty" yaml:"subnet,omitempty"`       // Subnet-name (subnet-name or subnet-name@project@domain). Looks up a subnet-id by name.
	SubnetId string `json:"subnet_id,omitempty" yaml:"subnet_id,omitempty"` // The ID of the subnet. One of subnet_id or port_id must be specified.
}

type RouterRouteSpec struct {
	Destination string `json:"destination,omitempty" yaml:"destination,omitempty"` // Route destination
	Nexthop     string `json:"nexthop,omitempty" yaml:"nexthop,omitempty"`         // Route nexthop
}

type SwiftAccountSpec struct {
	Enabled    *bool                `json:"enabled" yaml:"enabled,omitempty"`                 // Create a swift account
	Containers []SwiftContainerSpec `json:"containers,omitempty" yaml:"containers,omitempty"` // Containers
}

type SwiftContainerSpec struct {
	Name     string            `json:"name" yaml:"name"`                             // Container name
	Metadata map[string]string `json:"metadata,omitempty" yaml:"metadata,omitempty"` // Container metadata
}

// A designate project quota (see https://developer.openstack.org/api-ref/dns/?expanded=#quotas)
type DNSQuotaSpec struct {
	ApiExportSize    int `json:"api_export_size,omitempty" yaml:"api_export_size,omitempty"`
	Zones            int `json:"zones,omitempty" yaml:"zones,omitempty"`
	ZoneRecords      int `json:"zone_records,omitempty" yaml:"zone_records,omitempty"`
	ZoneRecordSets   int `json:"zone_recordsets,omitempty" yaml:"zone_recordsets,omitempty"`
	RecordsetRecords int `json:"recordset_records,omitempty" yaml:"recordset_records,omitempty"`
}

// A designate zone (see https://developer.openstack.org/api-ref/dns/?expanded=#zones)
type DNSZoneSpec struct {
	Name          string             `json:"name" yaml:"name"`                                   // DNS Name for the zone
	Type          string             `json:"type" yaml:"type"`                                   // Type of zone. PRIMARY is controlled by Designate, SECONDARY zones are slaved from another DNS Server. Defaults to PRIMARY
	Email         string             `json:"email" yaml:"email"`                                 // e-mail for the zone. Used in SOA records for the zone
	TTL           int                `json:"ttl,omitempty" yaml:"ttl,omitempty"`                 // TTL (Time to Live) for the zone.
	Description   string             `json:"description,omitempty" yaml:"description,omitempty"` // description of the zone
	DNSRecordsets []DNSRecordsetSpec `json:"recordsets,omitempty" yaml:"recordsets,omitempty"`   // The zones recordsets
}

// A designate zone (see https://developer.openstack.org/api-ref/dns/?expanded=#recordsets)
type DNSRecordsetSpec struct {
	Name        string   `json:"name" yaml:"name"`                                   // DNS Name for the recordset
	Type        string   `json:"type" yaml:"type"`                                   // They RRTYPE of the recordset.
	TTL         int      `json:"ttl,omitempty" yaml:"ttl,omitempty"`                 // TTL (Time to Live) for the recordset.
	Description string   `json:"description,omitempty" yaml:"description,omitempty"` // Description for this recordset
	Records     []string `json:"records,omitempty" yaml:"records,omitempty"`         // A list of data for this recordset. Each item will be a separate record in Designate These items should conform to the DNS spec for the record type - e.g. A records must be IPv4 addresses, CNAME records must be a hostname.
}

// A designate tsig key (see https://developer.openstack.org/api-ref/dns/#tsigkey)
type DNSTSIGKeySpec struct {
	Name       string `json:"name" yaml:"name"`                                   // Name for this tsigkey
	Algorithm  string `json:"algorithm,omitempty" yaml:"algorithm,omitempty"`     // The encryption algorithm for this tsigkey
	Secret     string `json:"secret,omitempty" yaml:"secret,omitempty"`           // The actual key to be used
	Scope      string `json:"scope,omitempty" yaml:"scope,omitempty"`             // scope for this tsigkey which can be either ZONE or POOL scope
	ResourceId string `json:"resource_id,omitempty" yaml:"resource_id,omitempty"` // resource id for this tsigkey which can be either zone or pool id
}

func (e *OpenstackSeedSpec) MergeRole(role string) {
	if e.Roles == nil {
		e.Roles = make([]string, 0)
	}
	for _, v := range e.Roles {
		if v == role {
			return
		}
	}
	glog.V(2).Info("append role ", role)
	e.Roles = append(e.Roles, role)
}

// MergeResourceClass merges resource-class by name into the spec
func (e *OpenstackSeedSpec) MergeResourceClass(resourceClass string) {
	if e.ResourceClasses == nil {
		e.ResourceClasses = make([]string, 0)
	}
	for _, v := range e.ResourceClasses {
		if v == resourceClass {
			return
		}
	}
	glog.V(2).Info("append resourceClass ", resourceClass)
	e.ResourceClasses = append(e.ResourceClasses, resourceClass)
}

func (e *OpenstackSeedSpec) MergeRegion(region RegionSpec) {
	if e.Regions == nil {
		e.Regions = make([]RegionSpec, 0)
	}
	for i, v := range e.Regions {
		if v.Region == region.Region {
			glog.V(2).Info("merge region ", region)
			utils.MergeStructFields(&v, region)
			e.Regions[i] = v
			return
		}
	}
	glog.V(2).Info("append region ", region)
	e.Regions = append(e.Regions, region)
}

func (e *OpenstackSeedSpec) MergeService(service ServiceSpec) {
	if e.Services == nil {
		e.Services = make([]ServiceSpec, 0)
	}
	for i, v := range e.Services {
		if v.Name == service.Name {
			glog.V(2).Info("merge service ", service)
			utils.MergeStructFields(&v, service)
			if len(service.Endpoints) > 0 {
				v.MergeEndpoints(service)
			}
			e.Services[i] = v
			return
		}
	}
	glog.V(2).Info("append service ", service)
	e.Services = append(e.Services, service)
}

func (e *ServiceSpec) MergeEndpoints(service ServiceSpec) {
	if e.Endpoints == nil {
		e.Endpoints = make([]EndpointSpec, 0)
	}
	for i, endpoint := range service.Endpoints {
		found := false
		for _, v := range e.Endpoints {
			if v.Interface == endpoint.Interface && v.Region == endpoint.Region {
				glog.V(2).Info("merge endpoint ", endpoint)
				utils.MergeStructFields(&v, endpoint)
				found = true
				e.Endpoints[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append endpoint ", endpoint)
			e.Endpoints = append(e.Endpoints, endpoint)
		}
	}
}

func (e *OpenstackSeedSpec) MergeFlavor(flavor FlavorSpec) {
	if e.Flavors == nil {
		e.Flavors = make([]FlavorSpec, 0)
	}
	for i, f := range e.Flavors {
		if f.Name == flavor.Name {
			glog.V(2).Info("merge flavor ", flavor)
			if f.ExtraSpecs == nil {
				f.ExtraSpecs = make(map[string]interface{})
			}
			for k, v := range flavor.ExtraSpecs {
				f.ExtraSpecs[k] = v
			}

			utils.MergeStructFields(&f, flavor)
			e.Flavors[i] = f
			return
		}
	}
	glog.V(2).Info("append flavor ", flavor)
	e.Flavors = append(e.Flavors, flavor)
}

func (e *OpenstackSeedSpec) MergeDomain(domain DomainSpec) {
	if e.Domains == nil {
		e.Domains = make([]DomainSpec, 0)
	}
	for i, v := range e.Domains {
		if v.Name == domain.Name {
			glog.V(2).Info("merge domain ", domain)
			utils.MergeStructFields(&v, domain)
			if len(domain.Users) > 0 {
				v.MergeUsers(domain)
			}
			if len(domain.Groups) > 0 {
				v.MergeGroups(domain)
			}
			if len(domain.Projects) > 0 {
				v.MergeProjects(domain)
			}
			if len(domain.RoleAssignments) > 0 {
				v.MergeRoleAssignments(domain)
			}
			v.MergeConfig(domain)
			e.Domains[i] = v
			return
		}
	}
	glog.V(2).Info("append domain ", domain)
	e.Domains = append(e.Domains, domain)
}

func (e *DomainSpec) MergeProjects(domain DomainSpec) {
	if e.Projects == nil {
		e.Projects = make([]ProjectSpec, 0)
	}
	for _, project := range domain.Projects {
		found := false
		for i, v := range e.Projects {
			if v.Name == project.Name {
				glog.V(2).Info("merge project ", project)
				utils.MergeStructFields(&v, project)
				if project.NetworkQuota != nil {
					if v.NetworkQuota == nil {
						v.NetworkQuota = new(NetworkQuotaSpec)
					}
					utils.MergeStructFields(v.NetworkQuota, project.NetworkQuota)
				}
				if len(project.RoleAssignments) > 0 {
					v.MergeRoleAssignments(project)
				}
				if len(project.Endpoints) > 0 {
					v.MergeEndpoints(project)
				}
				if len(project.AddressScopes) > 0 {
					v.MergeAddressScopes(project)
				}
				if len(project.SubnetPools) > 0 {
					v.MergeSubnetPools(project)
				}
				if len(project.Networks) > 0 {
					v.MergeNetworks(project)
				}
				if len(project.Routers) > 0 {
					v.MergeRouters(project)
				}
				if project.Swift != nil {
					v.MergeSwiftAccount(project)
				}
				if project.DNSQuota != nil {
					if v.DNSQuota == nil {
						v.DNSQuota = new(DNSQuotaSpec)
					}
					utils.MergeStructFields(v.DNSQuota, project.DNSQuota)
				}
				if len(project.DNSZones) > 0 {
					v.MergeDNSZones(project)
				}
				if len(project.DNSTSIGKeys) > 0 {
					v.MergeDNSTSIGKeys(project)
				}
				if len(project.Flavors) > 0 {
					v.Flavors = utils.MergeStringSlices(v.Flavors, project.Flavors)
				}
				e.Projects[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project ", project)
			e.Projects = append(e.Projects, project)
		}
	}
}

func (e *DomainSpec) MergeUsers(domain DomainSpec) {
	if e.Users == nil {
		e.Users = make([]UserSpec, 0)
	}
	for _, user := range domain.Users {
		found := false
		for i, v := range e.Users {
			if v.Name == user.Name {
				glog.V(2).Info("merge user ", user)
				utils.MergeStructFields(&v, user)
				if len(user.RoleAssignments) > 0 {
					v.MergeRoleAssignments(user)
				}
				e.Users[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append user ", user)
			e.Users = append(e.Users, user)
		}
	}
}

func (e *DomainSpec) MergeGroups(domain DomainSpec) {
	if e.Groups == nil {
		e.Groups = make([]GroupSpec, 0)
	}
	for i, group := range domain.Groups {
		found := false
		for _, v := range e.Groups {
			if v.Name == group.Name {
				glog.V(2).Info("merge group ", group)
				utils.MergeStructFields(&v, group)
				if len(group.Users) > 0 {
					v.MergeUsers(group)
				}
				if len(group.RoleAssignments) > 0 {
					v.MergeRoleAssignments(group)
				}
				e.Groups[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append group ", group)
			e.Groups = append(e.Groups, group)
		}
	}
}

func (e *DomainSpec) MergeRoleAssignments(domain DomainSpec) {
	if e.RoleAssignments == nil {
		e.RoleAssignments = make([]RoleAssignmentSpec, 0)
	}
	for _, ra := range domain.RoleAssignments {
		found := false
		for i, v := range e.RoleAssignments {
			if v.Role == ra.Role && v.User == ra.User && v.Group == ra.Group && v.Inherited == ra.Inherited {
				glog.V(2).Info("merge domain-role-assignment ", ra)
				utils.MergeStructFields(&v, ra)
				e.RoleAssignments[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append domain-role-assignment ", ra)
			e.RoleAssignments = append(e.RoleAssignments, ra)
		}
	}
}

func (e *DomainSpec) MergeConfig(domain DomainSpec) {
	if e.Config.IdentityConfig == nil {
		e.Config.IdentityConfig = make(map[string]string)
	}
	for k, v := range domain.Config.IdentityConfig {
		e.Config.IdentityConfig[k] = v
	}
	if e.Config.LdapConfig == nil {
		e.Config.LdapConfig = make(map[string]interface{})
	}
	for k, v := range domain.Config.LdapConfig {
		e.Config.LdapConfig[k] = v
	}
	if e.Config.CCAdConfig == nil {
		e.Config.CCAdConfig = make(map[string]interface{})
	}
	for k, v := range domain.Config.CCAdConfig {
		e.Config.CCAdConfig[k] = v
	}
}

func (e *ProjectSpec) MergeRoleAssignments(project ProjectSpec) {
	if e.RoleAssignments == nil {
		e.RoleAssignments = make([]RoleAssignmentSpec, 0)
	}
	for _, ra := range project.RoleAssignments {
		found := false
		for i, v := range e.RoleAssignments {
			if v.Role == ra.Role && v.User == ra.User && v.Group == ra.Group && v.Inherited == ra.Inherited {
				glog.V(2).Info("merge project-role-assignment ", ra)
				utils.MergeStructFields(&v, ra)
				e.RoleAssignments[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project-role-assignment ", ra)
			e.RoleAssignments = append(e.RoleAssignments, ra)
		}
	}
}

func (e *ProjectSpec) MergeEndpoints(project ProjectSpec) {
	if e.Endpoints == nil {
		e.Endpoints = make([]ProjectEndpointSpec, 0)
	}
	for _, ep := range project.Endpoints {
		found := false
		for i, v := range e.Endpoints {
			if v.Region == ep.Region && v.Service == ep.Service {
				glog.V(2).Info("merge project endpoint ", ep)
				utils.MergeStructFields(&v, ep)
				e.Endpoints[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project endpoint ", ep)
			e.Endpoints = append(e.Endpoints, ep)
		}
	}
}

func (e *ProjectSpec) MergeAddressScopes(project ProjectSpec) {
	if e.AddressScopes == nil {
		e.AddressScopes = make([]AddressScopeSpec, 0)
	}
	for _, as := range project.AddressScopes {
		found := false
		for i, v := range e.AddressScopes {
			if v.Name == as.Name {
				glog.V(2).Info("merge project address-scope ", as)
				utils.MergeStructFields(&v, as)
				if len(as.SubnetPools) > 0 {
					v.MergeSubnetPools(as)
				}
				e.AddressScopes[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project address-scope ", as)
			e.AddressScopes = append(e.AddressScopes, as)
		}
	}
}

func (e *ProjectSpec) MergeSubnetPools(project ProjectSpec) {
	if e.SubnetPools == nil {
		e.SubnetPools = make([]SubnetPoolSpec, 0)
	}
	for _, snp := range project.SubnetPools {
		found := false
		for i, v := range e.SubnetPools {
			if v.Name == snp.Name {
				glog.V(2).Info("merge project subnet-pool ", snp)
				utils.MergeStructFields(&v, snp)

				if len(snp.Prefixes) > 0 {
					v.Prefixes = utils.MergeStringSlices(v.Prefixes, snp.Prefixes)
				}
				e.SubnetPools[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project subnet-pool ", snp)
			e.SubnetPools = append(e.SubnetPools, snp)
		}
	}
}

func (e *ProjectSpec) MergeNetworks(project ProjectSpec) {
	if e.Networks == nil {
		e.Networks = make([]NetworkSpec, 0)
	}
	for _, n := range project.Networks {
		found := false
		for i, v := range e.Networks {
			if v.Name == n.Name {
				glog.V(2).Info("merge project network ", n)
				utils.MergeStructFields(&v, n)
				if len(n.Subnets) > 0 {
					v.MergeSubnets(n)
				}
				if len(n.Tags) > 0 {
					v.Tags = utils.MergeStringSlices(v.Tags, n.Tags)
				}
				e.Networks[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project network ", n)
			e.Networks = append(e.Networks, n)
		}
	}
}

func (e *ProjectSpec) MergeRouters(project ProjectSpec) {
	if e.Routers == nil {
		e.Routers = make([]RouterSpec, 0)
	}
	for _, r := range project.Routers {
		found := false
		for i, v := range e.Routers {
			if v.Name == r.Name {
				glog.V(2).Info("merge project router ", r)
				utils.MergeStructFields(&v, r)
				if r.ExternalGatewayInfo != nil {
					r.MergeExternalGatewayInfo(*r.ExternalGatewayInfo)
				}
				if len(r.RouterPorts) > 0 {
					v.MergeRouterPorts(r)
				}
				if len(r.Routes) > 0 {
					v.MergeRouterRoutes(r)
				}
				e.Routers[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project router ", r)
			e.Routers = append(e.Routers, r)
		}
	}
}

func (e *ProjectSpec) MergeSwiftAccount(project ProjectSpec) {
	if e.Swift == nil {
		e.Swift = new(SwiftAccountSpec)
	}
	utils.MergeStructFields(e.Swift, project.Swift)

	for _, c := range project.Swift.Containers {
		found := false
		for i, v := range e.Swift.Containers {
			if v.Name == c.Name {
				glog.V(2).Info("merge swift container ", c)
				utils.MergeStructFields(&v, c)
				e.Swift.Containers[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append swift container ", c)
			e.Swift.Containers = append(e.Swift.Containers, c)
		}
	}
}

func (e *ProjectSpec) MergeDNSZones(project ProjectSpec) {
	if e.DNSZones == nil {
		e.DNSZones = make([]DNSZoneSpec, 0)
	}

	for _, z := range project.DNSZones {
		if z.Type == "" {
			z.Type = "PRIMARY"
		}
		found := false
		for i, v := range e.DNSZones {
			if v.Type == "" {
				v.Type = "PRIMARY"
			}
			if v.Name == z.Name && v.Type == z.Type {
				glog.V(2).Info("merge project dns zone ", z)
				utils.MergeStructFields(&v, z)
				if len(z.DNSRecordsets) > 0 {
					v.MergeDNSRecordsets(z)
				}
				e.DNSZones[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project dns zone", z)
			e.DNSZones = append(e.DNSZones, z)
		}
	}
}

func (e *ProjectSpec) MergeDNSTSIGKeys(project ProjectSpec) {
	if e.DNSTSIGKeys == nil {
		e.DNSTSIGKeys = make([]DNSTSIGKeySpec, 0)
	}

	for _, z := range project.DNSTSIGKeys {
		found := false
		for i, v := range e.DNSTSIGKeys {
			if v.Name == z.Name {
				glog.V(2).Info("merge project dns tsig key ", z)
				utils.MergeStructFields(&v, z)
				e.DNSTSIGKeys[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append project dns tsig key ", z)
			e.DNSTSIGKeys = append(e.DNSTSIGKeys, z)
		}
	}
}

func (e *GroupSpec) MergeUsers(group GroupSpec) {
	if e.Users == nil {
		e.Users = make([]string, 0)
	}
	for _, user := range group.Users {
		found := false
		for _, v := range e.Users {
			if v == user {
				glog.V(2).Info("merge group user ", user)
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append group user ", user)
			e.Users = append(e.Users, user)
		}
	}
}

func (e *GroupSpec) MergeRoleAssignments(group GroupSpec) {
	if e.RoleAssignments == nil {
		e.RoleAssignments = make([]RoleAssignmentSpec, 0)
	}
	for _, ra := range group.RoleAssignments {
		found := false
		for i, v := range e.RoleAssignments {
			if v.Role == ra.Role && v.Project == ra.Project && v.Domain == ra.Domain && v.Inherited == ra.Inherited {
				glog.V(2).Info("merge group-role-assignment ", ra)
				utils.MergeStructFields(&v, ra)
				e.RoleAssignments[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append group-role-assignment ", ra)
			e.RoleAssignments = append(e.RoleAssignments, ra)
		}
	}
}

func (e *UserSpec) MergeRoleAssignments(user UserSpec) {
	if e.RoleAssignments == nil {
		e.RoleAssignments = make([]RoleAssignmentSpec, 0)
	}
	for _, ra := range user.RoleAssignments {
		found := false
		for i, v := range e.RoleAssignments {
			if v.Role == ra.Role && v.Project == ra.Project && v.Domain == ra.Domain && v.Inherited == ra.Inherited {
				glog.V(2).Info("merge user-role-assignment ", ra)
				utils.MergeStructFields(&v, ra)
				e.RoleAssignments[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append user-role-assignment ", ra)
			e.RoleAssignments = append(e.RoleAssignments, ra)
		}
	}
}

func (e *AddressScopeSpec) MergeSubnetPools(scope AddressScopeSpec) {
	if e.SubnetPools == nil {
		e.SubnetPools = make([]SubnetPoolSpec, 0)
	}
	for i, snp := range scope.SubnetPools {
		found := false
		for _, v := range e.SubnetPools {
			if v.Name == snp.Name {
				glog.V(2).Info("merge subnet-pool ", snp)
				utils.MergeStructFields(&v, snp)
				if len(snp.Prefixes) > 0 {
					v.Prefixes = utils.MergeStringSlices(v.Prefixes, snp.Prefixes)
				}
				found = true
				e.SubnetPools[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append subnet-pool ", snp)
			e.SubnetPools = append(e.SubnetPools, snp)
		}
	}
}

func (e *NetworkSpec) MergeSubnets(network NetworkSpec) {
	if e.Subnets == nil {
		e.Subnets = make([]SubnetSpec, 0)
	}
	for i, sn := range network.Subnets {
		found := false
		for _, v := range e.Subnets {
			if v.Name == sn.Name {
				glog.V(2).Info("merge subnet ", sn)
				utils.MergeStructFields(&v, sn)
				if len(sn.DNSNameServers) > 0 {
					v.DNSNameServers = utils.MergeStringSlices(sn.DNSNameServers, v.DNSNameServers)
				}
				if len(sn.AllocationPools) > 0 {
					v.AllocationPools = utils.MergeStringSlices(sn.AllocationPools, v.AllocationPools)
				}
				if len(sn.HostRoutes) > 0 {
					v.HostRoutes = utils.MergeStringSlices(sn.HostRoutes, v.HostRoutes)
				}
				found = true
				e.Subnets[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append subnet ", sn)
			e.Subnets = append(e.Subnets, sn)
		}
	}
}

func (e *RouterSpec) MergeRouterPorts(router RouterSpec) {
	if e.RouterPorts == nil {
		e.RouterPorts = make([]RouterPortSpec, 0)
	}
	for i, rp := range router.RouterPorts {
		found := false
		for _, v := range e.RouterPorts {
			if v == rp {
				glog.V(2).Info("merge port ", rp)
				utils.MergeStructFields(&v, rp)
				found = true
				e.RouterPorts[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append port ", rp)
			e.RouterPorts = append(e.RouterPorts, rp)
		}
	}
}

func (e *RouterSpec) MergeRouterRoutes(router RouterSpec) {
	if e.Routes == nil {
		e.Routes = make([]RouterRouteSpec, 0)
	}
	for i, rt := range router.Routes {
		found := false
		for _, v := range e.Routes {
			if v.Destination == rt.Destination {
				glog.V(2).Info("merge route ", rt)
				utils.MergeStructFields(&v, rt)
				found = true
				e.Routes[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append route ", rt)
			e.Routes = append(e.Routes, rt)
		}
	}
}

func (e *RouterSpec) MergeExternalGatewayInfo(egi ExternalGatewayInfoSpec) {
	if e.ExternalGatewayInfo == nil {
		e.ExternalGatewayInfo = new(ExternalGatewayInfoSpec)
		e.ExternalGatewayInfo.ExternalFixedIPs = make([]ExternalFixedIPsSpec, 0)
	}
	utils.MergeStructFields(e.ExternalGatewayInfo, egi)

	for i, efi := range egi.ExternalFixedIPs {
		found := false
		for _, v := range e.ExternalGatewayInfo.ExternalFixedIPs {
			if v.Subnet == efi.Subnet || v.SubnetId == efi.SubnetId {
				glog.V(2).Info("merge external fixed ip ", efi)
				utils.MergeStructFields(&v, efi)
				found = true
				e.ExternalGatewayInfo.ExternalFixedIPs[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append external fixed ip ", efi)
			e.ExternalGatewayInfo.ExternalFixedIPs = append(e.ExternalGatewayInfo.ExternalFixedIPs, efi)
		}
	}
}

func (e *DNSZoneSpec) MergeDNSRecordsets(zone DNSZoneSpec) {
	if e.DNSRecordsets == nil {
		e.DNSRecordsets = make([]DNSRecordsetSpec, 0)
	}
	for i, rs := range zone.DNSRecordsets {
		found := false
		for _, v := range e.DNSRecordsets {
			if v.Name == rs.Name && v.Type == rs.Type {
				glog.V(2).Info("merge recordset ", rs)
				utils.MergeStructFields(&v, rs)

				if len(rs.Records) > 0 {
					v.Records = utils.MergeStringSlices(v.Records, rs.Records)
				}

				found = true
				e.DNSRecordsets[i] = v
				break
			}
		}
		if !found {
			glog.V(2).Info("append recordset ", rs)
			e.DNSRecordsets = append(e.DNSRecordsets, rs)
		}
	}
}

func (e *OpenstackSeedSpec) MergeSpec(spec OpenstackSeedSpec) error {
	// sanitize and merge the spec
	for _, role := range spec.Roles {
		if role == "" {
			return errors.New("role name is required")
		}
		e.MergeRole(role)
	}

	for _, resourceClass := range spec.ResourceClasses {
		if resourceClass == "" {
			return errors.New("resourceClass name is required")
		}
		e.MergeResourceClass(resourceClass)
	}

	for _, region := range spec.Regions {
		if region.Region == "" {
			return errors.New("region name is required")
		}
		e.MergeRegion(region)
	}
	for _, service := range spec.Services {
		if service.Name == "" {
			return fmt.Errorf("%s: service name is required", service.Type)
		}
		//		if service.Type == "" {
		//			return fmt.Errorf("%s: service type is required", service.Name)
		//		}

		for _, endpoint := range service.Endpoints {
			if endpoint.Interface == "" {
				return fmt.Errorf("service %s: endpoint interface is required", service.Name)
			}
			ok, err := regexp.MatchString("admin|public|internal", endpoint.Interface)
			if !ok || err != nil {
				return fmt.Errorf("service %s, endpoint %s: invalid interface type", service.Name, endpoint.Interface)
			}
			if endpoint.URL == "" {
				return fmt.Errorf("service %s, endpoint %s: endpoint url is required", service.Name, endpoint.Interface)
			}
		}
		e.MergeService(service)
	}
	for _, domain := range spec.Domains {
		if domain.Name == "" {
			return fmt.Errorf("domain %s: a domain name is required", domain.Description)
		}
		for _, r := range domain.RoleAssignments {
			if r.User != "" && r.Group != "" {
				return fmt.Errorf("domain %s: role-assignment should target either user or a group, not both", domain.Name)
			}
			if r.User == "" && r.Group == "" {
				return fmt.Errorf("domain %s: role-assignment should target a user or a group", domain.Name)
			}
			if r.Role == "" {
				return fmt.Errorf("domain %s: role-assignment with no role", domain.Name)
			}
		}
		for _, project := range domain.Projects {
			if project.Name == "" {
				return fmt.Errorf("domain %s, project %s: a project name is required", domain.Name, project.Description)
			}
			for _, r := range project.RoleAssignments {
				if r.User != "" && r.Group != "" {
					return fmt.Errorf("project %s/%s: role-assignment should target either group or a user, not both", domain.Name, project.Name)
				}
				if r.User == "" && r.Group == "" {
					return fmt.Errorf("project %s/%s: role-assignment should target a group or a user", domain.Name, project.Name)
				}
				if r.Role == "" {
					return fmt.Errorf("project %s/%s: role-assignment with no role", domain.Name, project.Name)
				}
			}
		}
		for _, user := range domain.Users {
			if user.Name == "" {
				return fmt.Errorf("domain %s, user %s: a user name is required", domain.Name, user.Description)
			}
			for _, r := range user.RoleAssignments {
				if (r.Project != "" || r.ProjectID != "") && r.Domain != "" {
					return fmt.Errorf("user %s/%s: role-assignment should target either project or a domain, not both", domain.Name, user.Name)
				}
				if r.Project == "" && r.ProjectID == "" && r.Domain == "" {
					return fmt.Errorf("user %s/%s: role-assignment should target a project or a domain", domain.Name, user.Name)
				}
				if r.Role == "" {
					return fmt.Errorf("user %s/%s: role-assignment with no role", domain.Name, user.Name)
				}
			}
		}
		for _, group := range domain.Groups {
			if group.Name == "" {
				return fmt.Errorf("domain %s, group %s: a group name is required", domain.Name, group.Description)
			}
			for _, r := range group.RoleAssignments {
				if (r.Project != "" || r.ProjectID != "") && r.Domain != "" {
					return fmt.Errorf("group %s/%s: role-assignment should target either project or a domain, not both", domain.Name, group.Name)
				}
				if r.Project == "" && r.ProjectID == "" && r.Domain == "" {
					return fmt.Errorf("group %s/%s: role-assignment should target a project or a domain", domain.Name, group.Name)
				}
				if r.Role == "" {
					return fmt.Errorf("group %s/%s: role-assignment with no role", domain.Name, group.Name)
				}
			}
		}

		e.MergeDomain(domain)
	}

	for _, flavor := range spec.Flavors {
		if flavor.Id == "" {
			return errors.New("flavor id is required")
		}
		if flavor.Name == "" {
			return errors.New("flavor name is required")
		}
		e.MergeFlavor(flavor)
	}

	return nil
}
