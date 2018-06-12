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
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const OpenstackSeedResourcePlural = "openstackseeds"

// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +k8s:openapi-gen=true
type OpenstackSeed struct {
	metav1.TypeMeta `json:",inline"`
	// +k8s:openapi-gen=false
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   OpenstackSeedSpec    `json:"spec"`
	Status *OpenstackSeedStatus `json:"status,omitempty"`
}

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
type OpenstackSeedList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`

	Items []OpenstackSeed `json:"items"`
}

// +k8s:openapi-gen=true
type OpenstackSeedStatus struct {
	Processed           string          `json:"processed"`
	VisitedDependencies map[string]bool `json:"merged"`
}

// +k8s:openapi-gen=true
type OpenstackSeedSpec struct {
	Dependencies []string      `json:"requires,omitempty" yaml:"requires,omitempty"` // list of required specs that need to be resolved before the current one
	Roles        []string      `json:"roles,omitempty" yaml:"roles,omitempty"`       // list of keystone roles
	Regions      []RegionSpec  `json:"regions,omitempty" yaml:"regions,omitempty"`   // list keystone regions
	Services     []ServiceSpec `json:"services,omitempty" yaml:"services,omitempty"` // list keystone services and their endpoints
	Flavors      []FlavorSpec  `json:"flavors,omitempty" yaml:"flavors,omitempty"`   // list of nova flavors
	Domains      []DomainSpec  `json:"domains,omitempty" yaml:"domains,omitempty"`   // list keystone domains with their configuration, users, groups, projects, etc.
}

// A keystone region (see https://developer.openstack.org/api-ref/identity/v3/index.html#regions)
// +k8s:openapi-gen=true
type RegionSpec struct {
	Region       string `json:"id" yaml:"id"`                                           // the region id
	Description  string `json:"description,omitempty" yaml:"description,omitempty"`     // the regions description
	ParentRegion string `json:"parent_region,omitempty" yaml:"parent_region,omitempty"` // the (optional) id of the parent region
}

// A keystone service (see https://developer.openstack.org/api-ref/identity/v3/index.html#service-catalog-and-endpoints)
// +k8s:openapi-gen=true
type ServiceSpec struct {
	Name        string         `json:"name" yaml:"name"`                                   // service name
	Type        string         `json:"type" yaml:"type"`                                   // service type
	Description string         `json:"description,omitempty" yaml:"description,omitempty"` // description of the service
	Enabled     *bool          `json:"enabled,omitempty" yaml:"enabled,omitempty"`         // boolean flag to indicate if the service is enabled
	Endpoints   []EndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`     // list of service endpoints
}

// A keystone service endpoint (see https://developer.openstack.org/api-ref/identity/v3/index.html#service-catalog-and-endpoints)
// +k8s:openapi-gen=true
type EndpointSpec struct {
	Region    string `json:"region" yaml:"region"`                       // region-id
	Interface string `json:"interface" yaml:"interface"`                 // interface type (usually public, admin, internal)
	URL       string `json:"url" yaml:"url"`                             // the endpoints URL
	Enabled   *bool  `json:"enabled,omitempty" yaml:"enabled,omitempty"` // boolean flag to indicate if the endpoint is enabled
}

// A keystone domain (see https://developer.openstack.org/api-ref/identity/v3/index.html#domains)
// +k8s:openapi-gen=true
type DomainSpec struct {
	Name            string               `json:"name" yaml:"name"`                                   // domain name
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"` // domain description
	Enabled         *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`         // boolean flag to indicate if the domain is enabled
	Users           []UserSpec           `json:"users,omitempty" yaml:"users,omitempty"`             // list of domain users
	Groups          []GroupSpec          `json:"groups,omitempty" yaml:"groups,omitempty"`           // list of domain groups
	Projects        []ProjectSpec        `json:"projects,omitempty" yaml:"projects,omitempty"`       // list of domain projects
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of domain-role-assignments
	Config          *DomainConfigSpec    `json:"config,omitempty" yaml:"config,omitempty"`           // optional domain configuration
}

// A keystone domain configuation (see https://developer.openstack.org/api-ref/identity/v3/index.html#domain-configuration)
// +k8s:openapi-gen=true
type DomainConfigSpec struct {
	IdentityConfig *IdentityConfigSpec `json:"identity,omitempty" yaml:"identity,omitempty"` // the identity driver configuration settings
	LdapConfig     *LdapConfigSpec     `json:"ldap,omitempty" yaml:"ldap,omitempty"`         // the ldap driver configuration settings
}

// +k8s:openapi-gen=true
type IdentityConfigSpec struct {
	Driver string `json:"driver" yaml:"driver"` // Entry point for the domain-specific configuration driver in the 'keystone.resource.domain_config` namespace
}

// +k8s:openapi-gen=true
type LdapConfigSpec struct {
	Url        string `json:"url" yaml:"url"`                                     // URL(s) for connecting to the LDAP server. Multiple LDAP URLs may be specified as a comma separated string. The first URL to successfully bind is used for the connection.
	User       string `json:"user" yaml:"user"`                                   // The user name of the administrator bind DN to use when querying the LDAP server, if your LDAP server requires it.
	Password   string `json:"password" yaml:"password"`                           // The password of the administrator bind DN to use when querying the LDAP server, if your LDAP server requires it.
	Suffix     string `json:"suffix,omitempty" yaml:"suffix,omitempty"`           // The default LDAP server suffix to use, if a DN is not defined via either `[ldap] user_tree_dn` or `[ldap] group_tree_dn`.
	QueryScope string `json:"query_scope,omitempty" yaml:"query_scope,omitempty"` // The search scope which defines how deep to search within the search base. A  value of `one` (representing `oneLevel` or `singleLevel`) indicates a search of objects immediately below to the base object, but does not include the base object itself. A value of `sub` (representing `subtree` or `wholeSubtree`) indicates a search of both the base object itself and the entire subtree below it.
	PageSize   int    `json:"page_size,omitempty" yaml:"page_size,omitempty"`     // Defines the maximum number of results per page that keystone should request  from the LDAP server when listing objects. A value of zero (`0`) disables paging.

	UseTLS         *bool  `json:"use_tls,omitempty" yaml:"use_tls,omitempty"`
	TLSCACertFile  string `json:"tls_cacertfile,omitempty" yaml:"tls_cacertfile,omitempty"`
	TLSCACertDir   string `json:"tls_cacertdir,omitempty" yaml:"tls_cacertdir,omitempty"`
	TLSRequestCert string `json:"tls_req_cert,omitempty" yaml:"tls_req_cert,omitempty"`

	UsePool                *bool `json:"use_pool,omitempty" yaml:"use_pool,omitempty"`
	PoolSize               int   `json:"pool_size,omitempty" yaml:"pool_size,omitempty"`                               // The size of the LDAP connection pool
	PoolRetryMax           int   `json:"pool_retry_max,omitempty" yaml:"pool_retry_max,omitempty"`                     // The maximum number of times to attempt reconnecting to the LDAP server before aborting. A value of zero prevents retries.
	PoolRetryDelay         int   `json:"pool_retry_delay,omitempty" yaml:"pool_retry_delay,omitempty"`                 // The number of seconds to wait before attempting to reconnect to the LDAP server.
	PoolConnectionTimeout  int   `json:"pool_connection_timeout,omitempty" yaml:"pool_connection_timeout,omitempty"`   //
	PoolConnectionLifetime int   `json:"pool_connection_lifetime,omitempty" yaml:"pool_connection_lifetime,omitempty"` //

	UseAuthPool                *bool `json:"use_auth_pool,omitempty" yaml:"use_auth_pool,omitempty"`
	AuthPoolSize               int   `json:"auth_pool_size,omitempty" yaml:"auth_pool_size,omitempty"`                               // The size of the LDAP auth connection pool
	AuthPoolConnectionLifetime int   `json:"auth_pool_connection_lifetime,omitempty" yaml:"auth_pool_connection_lifetime,omitempty"` //

	AliasDereferencing string `json:"alias_dereferencing,omitempty" yaml:"alias_dereferencing,omitempty"`
	DebugLevel         int    `json:"debug_level,omitempty" yaml:"debug_level,omitempty"`

	UserTreeDN           string `json:"user_tree_dn,omitempty" yaml:"user_tree_dn,omitempty"`
	UserFilter           string `json:"user_filter,omitempty" yaml:"user_filter,omitempty"`
	UserObjectClass      string `json:"user_objectclass,omitempty" yaml:"user_objectclass,omitempty"`
	UserIdAttribute      string `json:"user_id_attribute,omitempty" yaml:"user_id_attribute,omitempty"`
	UserNameAttribute    string `json:"user_name_attribute,omitempty" yaml:"user_name_attribute,omitempty"`
	UserDescAttribute    string `json:"user_description_attribute,omitempty" yaml:"user_description_attribute,omitempty"`
	UserMailAttribute    string `json:"user_mail_attribute,omitempty" yaml:"user_mail_attribute,omitempty"`
	UserPassAttribute    string `json:"user_pass_attribute,omitempty" yaml:"user_pass_attribute,omitempty"`
	UserEnabledAttribute string `json:"user_enabled_attribute,omitempty" yaml:"user_enabled_attribute,omitempty"`
	UserEnabledMask      int    `json:"user_enabled_mask,omitempty" yaml:"user_enabled_mask,omitempty"`
	UserEnabledDefault   string `json:"user_enabled_default,omitempty" yaml:"user_enabled_default,omitempty"`
	UserAttributeIgnore  string `json:"user_attribute_ignore,omitempty" yaml:"user_attribute_ignore,omitempty"`
	UserAllowCreate      *bool  `json:"user_allow_create,omitempty" yaml:"user_allow_create,omitempty"`
	UserAllowUpdate      *bool  `json:"user_allow_update,omitempty" yaml:"user_allow_update,omitempty"`
	UserAllowDelete      *bool  `json:"user_allow_delete,omitempty" yaml:"user_allow_delete,omitempty"`

	GroupTreeDN          string `json:"group_tree_dn,omitempty" yaml:"group_tree_dn,omitempty"`
	GroupFilter          string `json:"group_filter,omitempty" yaml:"group_filter,omitempty"`
	GroupObjectClass     string `json:"group_objectclass,omitempty" yaml:"group_objectclass,omitempty"`
	GroupIdAttribute     string `json:"group_id_attribute,omitempty" yaml:"group_id_attribute,omitempty"`
	GroupNameAttribute   string `json:"group_name_attribute,omitempty" yaml:"group_name_attribute,omitempty"`
	GroupDescAttribute   string `json:"group_description_attribute,omitempty" yaml:"group_description_attribute,omitempty"`
	GroupMemberAttribute string `json:"group_member_attribute,omitempty" yaml:"group_member_attribute,omitempty"`
	GroupMembersAreIDs   *bool  `json:"group_members_are_ids,omitempty" yaml:"group_members_are_ids,omitempty"`
	GroupAttributeIgnore string `json:"group_attribute_ignore,omitempty" yaml:"group_attribute_ignore,omitempty"`
	GroupAllowCreate     *bool  `json:"group_allow_create,omitempty" yaml:"group_allow_create,omitempty"`
	GroupAllowUpdate     *bool  `json:"group_allow_update,omitempty" yaml:"group_allow_update,omitempty"`
	GroupAllowDelete     *bool  `json:"group_allow_delete,omitempty" yaml:"group_allow_delete,omitempty"`
}

// A keystone project (see https://developer.openstack.org/api-ref/identity/v3/index.html#projects)
// +k8s:openapi-gen=true
type ProjectSpec struct {
	Name            string                `json:"name" yaml:"name"`                                         // project name
	Description     string                `json:"description,omitempty" yaml:"description,omitempty"`       // project description
	Enabled         *bool                 `json:"enabled,omitempty" yaml:"enabled,omitempty"`               // boolean flag to indicate if the project is enabled
	Parent          string                `json:"parent,omitempty" yaml:"parent,omitempty"`                 // (optional) parent project name
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
// +k8s:openapi-gen=true
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
// +k8s:openapi-gen=true
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
// +k8s:openapi-gen=true
type UserSpec struct {
	Name             string               `json:"name" yaml:"name"`                                           // username
	Description      string               `json:"description,omitempty" yaml:"description,omitempty"`         // description of the user
	Password         string               `json:"password,omitempty" yaml:"password,omitempty"`               // password of the user (only evaluated on user creation)
	Enabled          *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`                 // boolean flag to indicate if the user is enabled
	RoleAssignments  []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`                     // list of the users role-assignments
	DefaultProjectID string               `json:"default_project,omitempty" yaml:"default_project,omitempty"` // default project scope for the user
}

// A keystone group (see https://developer.openstack.org/api-ref/identity/v3/#groups)
// +k8s:openapi-gen=true
type GroupSpec struct {
	Name            string               `json:"name" yaml:"name"`                                   // group name
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"` // description of the group
	Users           []string             `json:"users,omitempty" yaml:"users,omitempty"`             // a list of group members (user names)
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of the groups role-assignments
}

// A nova flavor (see https://developer.openstack.org/api-ref/compute/#flavors)
// +k8s:openapi-gen=true
type FlavorSpec struct {
	Name       string            `json:"name" yaml:"name"` // flavor name
	Id         string            `json:"id,omitempty" yaml:"id,omitempty"`
	Ram        int               `json:"ram,omitempty" yaml:"ram,omitempty"`
	Disk       int               `json:"disk,omitempty" yaml:"disk,omitempty"`
	Vcpus      int               `json:"vcpus,omitempty" yaml:"vcpus,omitempty"`
	Swap       int               `json:"swap,omitempty" yaml:"swap,omitempty"`
	RxTxfactor float32           `json:"rxtxfactor,omitempty" yaml:"rxtxfactor,omitempty"`
	IsPublic   *bool             `json:"is_public,omitempty" yaml:"is_public,omitempty"`
	Disabled   *bool             `json:"disabled,omitempty" yaml:"disabled,omitempty"`
	Ephemeral  int               `json:"ephemeral,omitempty" yaml:"ephemeral,omitempty"`
	ExtraSpecs map[string]string `json:"extra_specs,omitempty" yaml:"extra_specs,omitempty"` // list of extra specs
}

// A neutron address scope (see https://developer.openstack.org/api-ref/networking/v2/index.html  UNDOCUMENTED)
// +k8s:openapi-gen=true
type AddressScopeSpec struct {
	Name        string           `json:"name" yaml:"name"`                                     // address scope name
	IpVersion   int              `json:"ip_version" yaml:"ip_version"`                         // ip-version 4 or 6
	Shared      *bool            `json:"shared,omitempty" yaml:"shared,omitempty"`             // boolean flag to indicate if the address-scope is shared
	SubnetPools []SubnetPoolSpec `json:"subnet_pools,omitempty" yaml:"subnet_pools,omitempty"` // list of subnet-pools in the address-scope
}

// A neutron subnet pool (see https://developer.openstack.org/api-ref/networking/v2/index.html#subnet-pools)
// +k8s:openapi-gen=true
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
// +k8s:openapi-gen=true
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
// +k8s:openapi-gen=true
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
// +k8s:openapi-gen=true
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
	Tags            []string `json:"tags,omitempty" yaml:"tags,omitempty"`                           // List of subnet tags (see https://developer.openstack.org/api-ref/networking/v2/index.html#tag-extension-tags)
}

// A neutron router (see https://developer.openstack.org/api-ref/networking/v2/index.html#routers)
// +k8s:openapi-gen=true
type RouterSpec struct {
	Name                string                   `json:"name" yaml:"name"`                                         // router name
	AdminStateUp        *bool                    `json:"admin_state_up,omitempty" yaml:"admin_state_up,omitempty"` // The administrative state of the router, which is up (true) or down (false).
	Description         string                   `json:"description,omitempty" yaml:"description,omitempty"`       // description of the router
	ExternalGatewayInfo *ExternalGatewayInfoSpec `json:"external_gateway_info,omitempty" yaml:"external_gateway_info,omitempty"`
	Distributed         *bool                    `json:"distributed,omitempty" yaml:"distributed,omitempty"` // true indicates a distributed router. It is available when dvr extension is enabled.
	HA                  *bool                    `json:"ha,omitempty" yaml:"ha,omitempty"`                   // true indicates a highly-available router. It is available when l3-ha extension is enabled.
	RouterPorts         []RouterPortSpec         `json:"interfaces,omitempty" yaml:"interfaces,omitempty"`   //
}

// +k8s:openapi-gen=true
type ExternalGatewayInfoSpec struct {
	Network          string   `json:"network,omitempty" yaml:"network,omitempty"`                       // network-name in the same project
	NetworkId        string   `json:"network_id,omitempty" yaml:"network_id,omitempty"`                 // or network-id
	EnableSNAT       *bool    `json:"enable_snat,omitempty" yaml:"enable_snat,omitempty"`               // Enable Source NAT (SNAT) attribute. Default is true. To persist this attribute value, set the enable_snat_by_default option in the neutron.conf file. It is available when ext-gw-mode extension is enabled.
	ExternalFixedIPs []string `json:"external_fixed_ips,omitempty" yaml:"external_fixed_ips,omitempty"` // IP address(es) of the external gateway interface of the router. It is a list of IP addresses you would like to assign to the external gateway interface. Each element of ths list is a dictionary of ip_address and subnet_id.
}

// +k8s:openapi-gen=true
type RouterPortSpec struct {
	PortId   string `json:"port_id,omitempty" yaml:"port_id,omitempty"`     // port-id
	Subnet   string `json:"subnet,omitempty" yaml:"subnet,omitempty"`       // subnet-name within the routers project
	SubnetId string `json:"subnet_id,omitempty" yaml:"subnet_id,omitempty"` // subnet-id
}

// SwiftAccountSpec defines a swift account
// +k8s:openapi-gen=true
type SwiftAccountSpec struct {
	Enabled    *bool                `json:"enabled" yaml:"enabled,omitempty"`                 // Create a swift account
	Containers []SwiftContainerSpec `json:"containers,omitempty" yaml:"containers,omitempty"` // Containers
}

// SwiftContainerSpec defines a swift container
// +k8s:openapi-gen=true
type SwiftContainerSpec struct {
	Name     string            `json:"name" yaml:"name"`                             // Container name
	Metadata map[string]string `json:"metadata,omitempty" yaml:"metadata,omitempty"` // Container metadata
}

// DNSQuotaSpec defines a designate project quota (see https://developer.openstack.org/api-ref/dns/?expanded=#quotas)
// +k8s:openapi-gen=true
type DNSQuotaSpec struct {
	ApiExportSize    int `json:"api_export_size,omitempty" yaml:"api_export_size,omitempty"`
	Zones            int `json:"zones,omitempty" yaml:"zones,omitempty"`
	ZoneRecords      int `json:"zone_records,omitempty" yaml:"zone_records,omitempty"`
	ZoneRecordSets   int `json:"zone_recordsets,omitempty" yaml:"zone_recordsets,omitempty"`
	RecordsetRecords int `json:"recordset_records,omitempty" yaml:"recordset_records,omitempty"`
}

// DNSZoneSpec defines a designate zone (see https://developer.openstack.org/api-ref/dns/?expanded=#zones)
// +k8s:openapi-gen=true
type DNSZoneSpec struct {
	Name          string             `json:"name" yaml:"name"`                                   // DNS Name for the zone
	Type          string             `json:"type" yaml:"type"`                                   // Type of zone. PRIMARY is controlled by Designate, SECONDARY zones are slaved from another DNS Server. Defaults to PRIMARY
	Email         string             `json:"email" yaml:"email"`                                 // e-mail for the zone. Used in SOA records for the zone
	TTL           int                `json:"ttl,omitempty" yaml:"ttl,omitempty"`                 // TTL (Time to Live) for the zone.
	Description   string             `json:"description,omitempty" yaml:"description,omitempty"` // description of the zone
	DNSRecordsets []DNSRecordsetSpec `json:"recordsets,omitempty" yaml:"recordsets,omitempty"`   // The zones recordsets
}

// DNSRecordsetSpec defines a designate recordset (see https://developer.openstack.org/api-ref/dns/?expanded=#recordsets)
// +k8s:openapi-gen=true
type DNSRecordsetSpec struct {
	Name        string   `json:"name" yaml:"name"`                                   // DNS Name for the recordset
	Type        string   `json:"type" yaml:"type"`                                   // They RRTYPE of the recordset.
	TTL         int      `json:"ttl,omitempty" yaml:"ttl,omitempty"`                 // TTL (Time to Live) for the recordset.
	Description string   `json:"description,omitempty" yaml:"description,omitempty"` // Description for this recordset
	Records     []string `json:"records,omitempty" yaml:"records,omitempty"`         // A list of data for this recordset. Each item will be a separate record in Designate These items should conform to the DNS spec for the record type - e.g. A records must be IPv4 addresses, CNAME records must be a hostname.
}

// DNSTSIGKeySpec defines a designate tsig key (see https://developer.openstack.org/api-ref/dns/#tsigkey)
// +k8s:openapi-gen=true
type DNSTSIGKeySpec struct {
	Name       string `json:"name" yaml:"name"`                                   // Name for this tsigkey
	Algorithm  string `json:"algorithm,omitempty" yaml:"algorithm,omitempty"`     // The encryption algorithm for this tsigkey
	Secret     string `json:"secret,omitempty" yaml:"secret,omitempty"`           // The actual key to be used
	Scope      string `json:"scope,omitempty" yaml:"scope,omitempty"`             // scope for this tsigkey which can be either ZONE or POOL scope
	ResourceId string `json:"resource_id,omitempty" yaml:"resource_id,omitempty"` // resource id for this tsigkey which can be either zone or pool id
}
