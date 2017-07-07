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

package seeder

import (
	"encoding/json"
	"errors"
	"fmt"
	"github.com/getsentry/raven-go"
	"github.com/golang/glog"
	"k8s.io/client-go/1.5/kubernetes"
	"k8s.io/client-go/1.5/pkg/api"
	apierrors "k8s.io/client-go/1.5/pkg/api/errors"
	"k8s.io/client-go/1.5/pkg/api/meta"
	"k8s.io/client-go/1.5/pkg/api/unversioned"
	"k8s.io/client-go/1.5/pkg/api/v1"
	"k8s.io/client-go/1.5/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/1.5/pkg/runtime"
	"k8s.io/client-go/1.5/pkg/runtime/serializer"
	"k8s.io/client-go/1.5/pkg/util/wait"
	"k8s.io/client-go/1.5/rest"
	"net/http"
	"regexp"
	"time"
)

// The top level openstack seed element.
//
// It can have dependencies (that define elements that are refered to in the seed) that will be resolved before seeding the specs content.
//
// Cross kubernetes namespace dependencies can be defined by using a fully qualified **requires** notation that includes a namespace: namespace/specname
type OpenstackSeedSpec struct {
	Dependencies []string      `json:"requires,omitempty" yaml:"requires,omitempty"` // list of required specs that need to be resolved before the current one
	Roles        []string      `json:"roles,omitempty" yaml:"roles,omitempty"`       // list of keystone roles
	Regions      []RegionSpec  `json:"regions,omitempty" yaml:"regions,omitempty"`   // list keystone regions
	Services     []ServiceSpec `json:"services,omitempty" yaml:"services,omitempty"` // list keystone services and their endpoints
	Flavors      []FlavorSpec  `json:"flavors,omitempty" yaml:"flavors,omitempty"`   // list of nova flavors
	Domains      []DomainSpec  `json:"domains,omitempty" yaml:"domains,omitempty"`   // list keystone domains with their configuration, users, groups, projects, etc.
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
	ParentId        string                `json:"parent_id,omitempty" yaml:"parent_id,omitempty"`           // (optional) parent project id
	IsDomain        *bool                 `json:"is_domain,omitempty" yaml:"is_domain,omitempty"`           // is the project actually a domain?
	Endpoints       []ProjectEndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`           // list of project endpoint filters
	RoleAssignments []RoleAssignmentSpec  `json:"roles,omitempty" yaml:"roles,omitempty"`                   // list of project-role-assignments
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
	Role      string `json:"role" yaml:"role"`                               // the role name
	Domain    string `json:"domain,omitempty" yaml:"domain,omitempty"`       // domain-role-assigment: the domain name
	Project   string `json:"project,omitempty" yaml:"project,omitempty"`     // project-role-assignment: the project name
	Group     string `json:"group,omitempty" yaml:"group,omitempty"`         // group name (for project/domain group-role-assignment)
	User      string `json:"user,omitempty" yaml:"user,omitempty"`           // user name (for project/domain user-role-assignment)
	Inherited *bool  `json:"inherited,omitempty" yaml:"inherited,omitempty"` // boolean flag to indicate if the role-assignment should be inherited
}

// A keystone user (see https://developer.openstack.org/api-ref/identity/v3/#users)
type UserSpec struct {
	Name            string               `json:"name" yaml:"name"`                                   // username
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"` // description of the user
	Password        string               `json:"password,omitempty" yaml:"password,omitempty"`       // password of the user (only evaluated on user creation)
	Enabled         *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`         // boolean flag to indicate if the user is enabled
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of the users role-assignments
}

// A keystone group (see https://developer.openstack.org/api-ref/identity/v3/#groups)
type GroupSpec struct {
	Name            string               `json:"name" yaml:"name"`                                   // group name
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"` // description of the group
	Users           []string             `json:"users,omitempty" yaml:"users,omitempty"`             // a list of group members (user names)
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of the groups role-assignments
}

// A nova flavor (see https://developer.openstack.org/api-ref/compute/#flavors)
//
// This has not been tested and should be considered WIP
type FlavorSpec struct {
	Name       string  `json:"name" yaml:"name"` // flavor name
	Id         string  `json:"id,omitempty" yaml:"id,omitempty"`
	Ram        int     `json:"ram,omitempty" yaml:"ram,omitempty"`
	Disk       int     `json:"disk,omitempty" yaml:"disk,omitempty"`
	Vcpus      int     `json:"vcpus,omitempty" yaml:"vcpus,omitempty"`
	Swap       int     `json:"swap,omitempty" yaml:"swap,omitempty"`
	RxTxfactor float32 `json:"rxtxfactor,omitempty" yaml:"rxtxfactor,omitempty"`
	IsPublic   *bool   `json:"is_public,omitempty" yaml:"is_public,omitempty"`
	Disabled   *bool   `json:"disabled,omitempty" yaml:"disabled,omitempty"`
	Ephemeral  int     `json:"ephemeral,omitempty" yaml:"ephemeral,omitempty"`
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
	IPV6AddressMode string   `json:"ipv6_address_mode,omitempty" yaml:"ipv6_address_mode,omitempty"` // The IPv6 address modes specifies mechanisms for assigning IP addresses. Value is slaac, dhcpv6-stateful, dhcpv6-stateless.
	IPV6RaMode      string   `json:"ipv6_ra_mode,omitempty" yaml:"ipv6_ra_mode,omitempty"`           // The IPv6 router advertisement specifies whether the networking service should transmit ICMPv6 packets, for a subnet. Value is slaac, dhcpv6-stateful, dhcpv6-stateless.
	SegmentlId      string   `json:"segment_id,omitempty" yaml:"segment_id,omitempty"`               // The ID of a network segment the subnet is associated with. It is available when segment extension is enabled.
	SubnetPoolId    string   `json:"subnetpool_id,omitempty" yaml:"subnetpool_id,omitempty"`         // Subnet-pool ID
	SubnetPool      string   `json:"subnetpool,omitempty" yaml:"subnetpool,omitempty"`               // Subnet-pool name within teh subnets project
}

// A neutron router (see https://developer.openstack.org/api-ref/networking/v2/index.html#routers)
type RouterSpec struct {
	Name                string                   `json:"name" yaml:"name"`                                         // router name
	AdminStateUp        *bool                    `json:"admin_state_up,omitempty" yaml:"admin_state_up,omitempty"` // The administrative state of the router, which is up (true) or down (false).
	Description         string                   `json:"description,omitempty" yaml:"description,omitempty"`       // description of the router
	ExternalGatewayInfo *ExternalGatewayInfoSpec `json:"external_gateway_info,omitempty" yaml:"external_gateway_info,omitempty"`
	Distributed         *bool                    `json:"distributed,omitempty" yaml:"distributed,omitempty"` // true indicates a distributed router. It is available when dvr extension is enabled.
	HA                  *bool                    `json:"ha,omitempty" yaml:"ha,omitempty"`                   // true indicates a highly-available router. It is available when l3-ha extension is enabled.
	RouterPorts         []RouterPortSpec         `json:"interfaces,omitempty" yaml:"interfaces,omitempty"`   //
}

type ExternalGatewayInfoSpec struct {
	Network          string   `json:"network,omitempty" yaml:"network,omitempty"`                       // network-name in the same project
	NetworkId        string   `json:"network_id,omitempty" yaml:"network_id,omitempty"`                 // or network-id
	EnableSNAT       *bool    `json:"enable_snat,omitempty" yaml:"enable_snat,omitempty"`               // Enable Source NAT (SNAT) attribute. Default is true. To persist this attribute value, set the enable_snat_by_default option in the neutron.conf file. It is available when ext-gw-mode extension is enabled.
	ExternalFixedIPs []string `json:"external_fixed_ips,omitempty" yaml:"external_fixed_ips,omitempty"` // IP address(es) of the external gateway interface of the router. It is a list of IP addresses you would like to assign to the external gateway interface. Each element of ths list is a dictionary of ip_address and subnet_id.
}

type RouterPortSpec struct {
	PortId   string `json:"port_id,omitempty" yaml:"port_id,omitempty"`     // port-id
	Subnet   string `json:"subnet,omitempty" yaml:"subnet,omitempty"`       // subnet-name within the routers project
	SubnetId string `json:"subnet_id,omitempty" yaml:"subnet_id,omitempty"` // subnet-id
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

type OpenstackSeed struct {
	unversioned.TypeMeta `json:",inline"`
	Metadata             api.ObjectMeta `json:"metadata"`
	VisitedDependencies  map[string]bool
	Spec                 OpenstackSeedSpec `json:"spec" yaml:"spec"`
}

type OpenstackSeedList struct {
	unversioned.TypeMeta `json:",inline"`
	Metadata             unversioned.ListMeta `json:"metadata"`

	Items []OpenstackSeed `json:"items" yaml:"items"`
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

func (e *OpenstackSeedSpec) MergeRegion(region RegionSpec) {
	if e.Regions == nil {
		e.Regions = make([]RegionSpec, 0)
	}
	for i, v := range e.Regions {
		if v.Region == region.Region {
			glog.V(2).Info("merge region ", region)
			MergeStructFields(&v, region)
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
			MergeStructFields(&v, service)
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
				MergeStructFields(&v, endpoint)
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
	for i, v := range e.Flavors {
		if v.Name == flavor.Name {
			glog.V(2).Info("merge flavor ", flavor)
			MergeStructFields(&v, flavor)
			e.Flavors[i] = v
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
			MergeStructFields(&v, domain)
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
				MergeStructFields(&v, project)
				if project.NetworkQuota != nil {
					MergeStructFields(v.NetworkQuota, project.NetworkQuota)
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
					MergeStructFields(v.DNSQuota, project.DNSQuota)
				}
				if len(project.DNSZones) > 0 {
					v.MergeDNSZones(project)
				}
				if len(project.DNSTSIGKeys) > 0 {
					v.MergeDNSTSIGKeys(project)
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
				MergeStructFields(&v, user)
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
				MergeStructFields(&v, group)
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
			if v.Role == ra.Role && v.User == ra.User && v.Group == ra.Group {
				glog.V(2).Info("merge domain-role-assignment ", ra)
				MergeStructFields(&v, ra)
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
			if v.Role == ra.Role && v.User == ra.User && v.Group == ra.Group {
				glog.V(2).Info("merge project-role-assignment ", ra)
				MergeStructFields(&v, ra)
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
				MergeStructFields(&v, ep)
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
				MergeStructFields(&v, as)
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
				MergeStructFields(&v, snp)

				if len(snp.Prefixes) > 0 {
					v.Prefixes = MergeStringSlices(v.Prefixes, snp.Prefixes)
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
				MergeStructFields(&v, n)
				if len(n.Subnets) > 0 {
					v.MergeSubnets(n)
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
				MergeStructFields(&v, r)
				if r.ExternalGatewayInfo != nil {
					MergeStructFields(v.ExternalGatewayInfo, r.ExternalGatewayInfo)
					if len(r.ExternalGatewayInfo.ExternalFixedIPs) > 0 {
						v.ExternalGatewayInfo.ExternalFixedIPs = MergeStringSlices(r.ExternalGatewayInfo.ExternalFixedIPs, v.ExternalGatewayInfo.ExternalFixedIPs)
					}
				}
				if len(r.RouterPorts) > 0 {
					v.MergeRouterPorts(r)
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
	MergeStructFields(e.Swift, project.Swift)

	for _, c := range project.Swift.Containers {
		found := false
		for i, v := range e.Swift.Containers {
			if v.Name == c.Name {
				glog.V(2).Info("merge swift container ", c)
				MergeStructFields(&v, c)
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
				MergeStructFields(&v, z)
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
				MergeStructFields(&v, z)
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
			if v.Role == ra.Role && v.Project == ra.Project && v.Domain == ra.Domain {
				glog.V(2).Info("merge group-role-assignment ", ra)
				MergeStructFields(&v, ra)
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
			if v.Role == ra.Role && v.Project == ra.Project && v.Domain == ra.Domain {
				glog.V(2).Info("merge user-role-assignment ", ra)
				MergeStructFields(&v, ra)
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
				MergeStructFields(&v, snp)
				if len(snp.Prefixes) > 0 {
					v.Prefixes = MergeStringSlices(v.Prefixes, snp.Prefixes)
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
				MergeStructFields(&v, sn)
				if len(sn.DNSNameServers) > 0 {
					v.DNSNameServers = MergeStringSlices(sn.DNSNameServers, v.DNSNameServers)
				}
				if len(sn.AllocationPools) > 0 {
					v.AllocationPools = MergeStringSlices(sn.AllocationPools, v.AllocationPools)
				}
				if len(sn.HostRoutes) > 0 {
					v.HostRoutes = MergeStringSlices(sn.HostRoutes, v.HostRoutes)
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
				MergeStructFields(&v, rp)
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

func (e *DNSZoneSpec) MergeDNSRecordsets(zone DNSZoneSpec) {
	if e.DNSRecordsets == nil {
		e.DNSRecordsets = make([]DNSRecordsetSpec, 0)
	}
	for i, rs := range zone.DNSRecordsets {
		found := false
		for _, v := range e.DNSRecordsets {
			if v.Name == rs.Name && v.Type == rs.Type {
				glog.V(2).Info("merge recordset ", rs)
				MergeStructFields(&v, rs)

				if len(rs.Records) > 0 {
					v.Records = MergeStringSlices(v.Records, rs.Records)
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

func NewOpenstackSeedClientForConfig(c *rest.Config) (*rest.RESTClient, error) {
	c.APIPath = "/apis"
	c.GroupVersion = &unversioned.GroupVersion{
		Group:   "openstack.stable.sap.cc",
		Version: "v1",
	}
	c.NegotiatedSerializer = serializer.DirectCodecFactory{CodecFactory: api.Codecs}

	schemeBuilder := runtime.NewSchemeBuilder(
		func(scheme *runtime.Scheme) error {
			scheme.AddKnownTypes(
				*c.GroupVersion,
				&OpenstackSeed{},
				&OpenstackSeedList{},
				&api.ListOptions{},
				&api.DeleteOptions{},
			)
			return nil
		})
	schemeBuilder.AddToScheme(api.Scheme)

	return rest.RESTClientFor(c)
}

func EnsureOpenstackSeedThirdPartyResource(client *kubernetes.Clientset) error {
	const name = "openstack-seed.openstack.stable.sap.cc"

	_, err := client.Extensions().ThirdPartyResources().Get(name)
	if err != nil {
		// The resource doesn't exist, so we create it.
		newResource := v1beta1.ThirdPartyResource{
			ObjectMeta: v1.ObjectMeta{
				Name: name,
			},
			Description: "A specification of an openstack seed",
			Versions: []v1beta1.APIVersion{
				{Name: "v1"},
			},
		}

		_, err = client.Extensions().ThirdPartyResources().Create(&newResource)

		// We have to wait for the TPR to be ready. Otherwise the initial watch may fail.
		wait.Poll(3*time.Second, 30*time.Second, func() (bool, error) {
			_, err := client.Extensions().ThirdPartyResources().Get(name)
			if err != nil {
				// RESTClient returns *errors.StatusError for any status codes < 200 or > 206
				// and http.Client.Do errors are returned directly.
				if se, ok := err.(*apierrors.StatusError); ok {
					if se.Status().Code == http.StatusNotFound {
						return false, nil
					}
				}
				return false, err
			}
			return true, nil
		})
	}

	return err
}

func (e *OpenstackSeedSpec) MergeSpec(spec OpenstackSeedSpec) error {
	// sanitize and merge the spec
	for _, role := range spec.Roles {
		if role == "" {
			return errors.New("role name is required")
		}
		e.MergeRole(role)
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
			return fmt.Errorf("domain %s: a domain mame is required", domain.Description)
		}
		for _, r := range domain.RoleAssignments {
			if r.User != "" && r.Group != "" {
				return fmt.Errorf("domain %s: role-assignment should target either user or a group, not both.", domain.Name)
			}
			if r.User == "" && r.Group == "" {
				return fmt.Errorf("domain %s: role-assignment should target a user or a group.", domain.Name)
			}
			if r.Role == "" {
				return fmt.Errorf("domain %s: role-assignment with no role.", domain.Name)
			}
		}
		for _, project := range domain.Projects {
			if project.Name == "" {
				return fmt.Errorf("domain %s, project %s: a project mame is required", domain.Name, project.Description)
			}
			for _, r := range project.RoleAssignments {
				if r.User != "" && r.Group != "" {
					return fmt.Errorf("project %s/%s: role-assignment should target either group or a user, not both.", domain.Name, project.Name)
				}
				if r.User == "" && r.Group == "" {
					return fmt.Errorf("project %s/%s: role-assignment should target a group or a user.", domain.Name, project.Name)
				}
				if r.Role == "" {
					return fmt.Errorf("project %s/%s: role-assignment with no role.", domain.Name, project.Name)
				}
			}
		}
		for _, user := range domain.Users {
			if user.Name == "" {
				return fmt.Errorf("domain %s, user %s: a user mame is required", domain.Name, user.Description)
			}
			for _, r := range user.RoleAssignments {
				if r.Project != "" && r.Domain != "" {
					return fmt.Errorf("user %s/%s: role-assignment should target either project or a domain, not both.", domain.Name, user.Name)
				}
				if r.Project == "" && r.Domain == "" {
					return fmt.Errorf("user %s/%s: role-assignment should target a project or a domain.", domain.Name, user.Name)
				}
				if r.Role == "" {
					return fmt.Errorf("user %s/%s: role-assignment with no role.", domain.Name, user.Name)
				}
			}
		}
		for _, group := range domain.Groups {
			if group.Name == "" {
				return fmt.Errorf("domain %s, group %s: a group mame is required", domain.Name, group.Description)
			}
			for _, r := range group.RoleAssignments {
				if r.Project != "" && r.Domain != "" {
					return fmt.Errorf("group %s/%s: role-assignment should target either project or a domain, not both.", domain.Name, group.Name)
				}
				if r.Project == "" && r.Domain == "" {
					return fmt.Errorf("group %s/%s: role-assignment should target a project or a domain.", domain.Name, group.Name)
				}
				if r.Role == "" {
					return fmt.Errorf("group %s/%s: role-assignment with no role.", domain.Name, group.Name)
				}
			}
		}

		e.MergeDomain(domain)
	}

	for _, flavor := range spec.Flavors {
		if flavor.Name == "" {
			return errors.New("flavor name is required")
		}
		e.MergeFlavor(flavor)
	}

	return nil
}

// The code below is used only to work around a known problem with third-party
// resources and ugorji. If/when these issues are resolved, the code below
// should no longer be required.
//

func (s *OpenstackSeed) GetObjectKind() unversioned.ObjectKind {
	return &s.TypeMeta
}

func (s *OpenstackSeed) GetObjectMeta() meta.Object {
	return &s.Metadata
}

func (sl *OpenstackSeedList) GetObjectKind() unversioned.ObjectKind {
	return &sl.TypeMeta
}

func (sl *OpenstackSeedList) GetListMeta() unversioned.List {
	return &sl.Metadata
}

type OpenstackSeedListCopy OpenstackSeedList
type OpenstackSeedCopy OpenstackSeed

func (e *OpenstackSeed) UnmarshalJSON(data []byte) error {
	tmp := OpenstackSeedCopy{}
	err := json.Unmarshal(data, &tmp)
	if err != nil {
		msg := fmt.Sprintf("openstackseed '%s/%s' is invalid: %s", tmp.Metadata.Namespace, tmp.Metadata.Name, err.Error())
		raven.CaptureMessage(msg, nil)
		glog.Errorf(msg)
		return nil
	}
	tmp2 := OpenstackSeed(tmp)
	*e = tmp2
	return nil
}

func (el *OpenstackSeedList) UnmarshalJSON(data []byte) error {
	tmp := OpenstackSeedListCopy{}
	err := json.Unmarshal(data, &tmp)
	if err != nil {
		glog.Errorf("ERROR: invalid OpenstackSeedList: %s", err)
		return nil
	}
	tmp2 := OpenstackSeedList(tmp)
	*el = tmp2
	return nil
}
