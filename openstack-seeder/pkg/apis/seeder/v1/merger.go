/*
Copyright 2017 SAP SE

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

package v1

import (
	"errors"
	"fmt"
	"regexp"

	"github.com/golang/glog"
	utils "github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder"
)

func (e *OpenstackSeedSpec) MergeRole(role RoleSpec) {
	if e.Roles == nil {
		e.Roles = make([]RoleSpec, 0)
	}
	for i, v := range e.Roles {
		if v.Name == role.Name {
			glog.V(2).Info("merge role ", role.Name)
			utils.MergeStructFields(&v, role)
			e.Roles[i] = v
		}
	}
	glog.V(2).Info("append role ", role)
	e.Roles = append(e.Roles, role)
}

func (e *OpenstackSeedSpec) MergeRoleInference(roleInference RoleInferenceSpec) {
	if e.RoleInferences == nil {
		e.RoleInferences = make([]RoleInferenceSpec, 0)
	}
	for i, v := range e.RoleInferences {
		if v.PriorRole == roleInference.PriorRole && v.ImpliedRole == roleInference.ImpliedRole {
			glog.V(2).Info("merge role-inference ", roleInference.PriorRole)
			utils.MergeStructFields(&v, roleInference)
			e.RoleInferences[i] = v
			return
		}
	}
	glog.V(2).Info("append role-inference ", roleInference)
	e.RoleInferences = append(e.RoleInferences, roleInference)
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
				f.ExtraSpecs = make(map[string]string)
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

func (e *OpenstackSeedSpec) MergeShareType(t ShareTypeSpec) {
	if e.ShareTypes == nil {
		e.ShareTypes = make([]ShareTypeSpec, 0)
	}
	for i, s := range e.ShareTypes {
		if s.Name == t.Name {
			glog.V(2).Info("merge Manila share type ", t)
			if s.ExtraSpecs == nil {
				s.ExtraSpecs = make(map[string]string)
			}
			for k, v := range t.ExtraSpecs {
				s.ExtraSpecs[k] = v
			}
			utils.MergeStructFields(&s, t)
			e.ShareTypes[i] = s
			return
		}
	}
	glog.V(2).Info("append Manila share type ", t)
	e.ShareTypes = append(e.ShareTypes, t)
}

func (e *OpenstackSeedSpec) MergeVolumeType(t VolumeTypeSpec) {
	if e.VolumeTypes == nil {
		e.VolumeTypes = make([]VolumeTypeSpec, 0)
	}
	for i, s := range e.VolumeTypes {
		if s.Name == t.Name {
			glog.V(2).Info("merge Cinder volume type ", t)
			if s.ExtraSpecs == nil {
				s.ExtraSpecs = make(map[string]string)
			}
			for k, v := range t.ExtraSpecs {
				s.ExtraSpecs[k] = v
			}
			utils.MergeStructFields(&s, t)
			e.VolumeTypes[i] = s
			return
		}
	}
	glog.V(2).Info("append cinder volume type ", t)
	e.VolumeTypes = append(e.VolumeTypes, t)
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
			if len(domain.Roles) > 0 {
				v.MergeRoles(domain)
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

func (e *OpenstackSeedSpec) MergeRbacPolicy(rbac RBACPolicySpec) {
	if e.RBACPolicies == nil {
		e.RBACPolicies = make([]RBACPolicySpec, 0)
	}
	for _, v := range e.RBACPolicies {
		if v.ObjectType == rbac.ObjectType && v.ObjectName == rbac.ObjectName && v.Action == rbac.Action && v.TargetTenantName == rbac.TargetTenantName {
			return
		}
	}
	glog.V(2).Info("append rbac ", rbac)
	e.RBACPolicies = append(e.RBACPolicies, rbac)
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
				if len(project.Ec2Creds) > 0 {
					v.MergeEc2Creds(project)
				}
				if len(project.Flavors) > 0 {
					v.Flavors = utils.MergeStringSlices(v.Flavors, project.Flavors)
				}
				if len(project.ShareTypes) > 0 {
					v.ShareTypes = utils.MergeStringSlices(v.ShareTypes, project.ShareTypes)
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
	for _, group := range domain.Groups {
		found := false
		for i, v := range e.Groups {
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

func (e *DomainSpec) MergeRoles(domain DomainSpec) {
	if e.Roles == nil {
		e.Roles = make([]RoleSpec, 0)
	}
	for _, ra := range domain.Roles {
		found := false
		for i, v := range e.Roles {
			if v.Name == ra.Name {
				glog.V(2).Info("merge domain-role ", ra)
				utils.MergeStructFields(&v, ra)
				e.Roles[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append domain-role ", ra)
			e.Roles = append(e.Roles, ra)
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
	if domain.Config != nil {
		if e.Config == nil {
			e.Config = new(DomainConfigSpec)
		}
		utils.MergeStructFields(domain.Config, e.Config)

		if domain.Config.IdentityConfig != nil {
			if e.Config.IdentityConfig == nil {
				e.Config.IdentityConfig = new(IdentityConfigSpec)
			}
			utils.MergeStructFields(domain.Config.IdentityConfig, e.Config.IdentityConfig)
		}

		if domain.Config.LdapConfig != nil {
			if e.Config.LdapConfig == nil {
				e.Config.LdapConfig = new(LdapConfigSpec)
			}
			utils.MergeStructFields(domain.Config.LdapConfig, e.Config.LdapConfig)
		}
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

func (e *ProjectSpec) MergeEc2Creds(project ProjectSpec) {
	if e.Ec2Creds == nil {
		e.Ec2Creds = make([]Ec2CredSpec, 0)
	}
	for _, z := range project.Ec2Creds {
		found := false
		for i, v := range e.Ec2Creds {
			if v.User == z.User {
				glog.V(2).Info("merge ec2 credentials", z)
				utils.MergeStructFields(&v, z)
				e.Ec2Creds[i] = v
				found = true
				break
			}
		}
		if !found {
			glog.V(2).Info("append ec2 credentials", z)
			e.Ec2Creds = append(e.Ec2Creds, z)
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
		if role.Name == "" {
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
			return fmt.Errorf("domain %s: a domain name is required", domain.Description)
		}
		for _, role := range spec.Roles {
			if role.Name == "" {
				return fmt.Errorf("domain %s: a domain role name is required", domain.Name)
			}
			e.MergeRole(role)
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
			if r.System != "" || r.Project != "" || r.ProjectID != "" {
				return fmt.Errorf("domain %s: domain-role-assignment should not also target a project or system", domain.Name)
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
				if r.System != "" || r.Domain != "" {
					return fmt.Errorf("project %s: project-role-assignment should not also target a domain or system", domain.Name)
				}
			}
		}
		for _, user := range domain.Users {
			if user.Name == "" {
				return fmt.Errorf("domain %s, user %s: a user name is required", domain.Name, user.Description)
			}
			for _, r := range user.RoleAssignments {
				if r.System != "" {
					if r.System != "all" {
						return fmt.Errorf("user %s/%s: system-role-assignment can curently only target 'all'", domain.Name, user.Name)
					}
				} else {
					if (r.Project != "" || r.ProjectID != "") && r.Domain != "" {
						return fmt.Errorf("user %s/%s: role-assignment should target either project or a domain, not both", domain.Name, user.Name)
					}
					if r.Project == "" && r.ProjectID == "" && r.Domain == "" {
						return fmt.Errorf("user %s/%s: role-assignment should target a project or a domain", domain.Name, user.Name)
					}
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
				if r.System != "" {
					if r.System != "all" {
						return fmt.Errorf("group %s/%s: system-role-assignment can curently only target 'all'", domain.Name, group.Name)
					}
				} else {
					if (r.Project != "" || r.ProjectID != "") && r.Domain != "" {
						return fmt.Errorf("group %s/%s: role-assignment should target either project or a domain, not both", domain.Name, group.Name)
					}
					if r.Project == "" && r.ProjectID == "" && r.Domain == "" {
						return fmt.Errorf("group %s/%s: role-assignment should target a project or a domain", domain.Name, group.Name)
					}
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

	for _, shareType := range spec.ShareTypes {
		if shareType.Name == "" {
			return errors.New("Share type name is required")
		}
		e.MergeShareType(shareType)
	}

	for _, volumeType := range spec.VolumeTypes {
		if volumeType.Name == "" {
			return errors.New("volume type name is required")
		}
		e.MergeVolumeType(volumeType)
	}

	for _, roleInference := range spec.RoleInferences {
		if roleInference.PriorRole == "" {
			return errors.New("prior-role name is required")
		}
		if roleInference.ImpliedRole == "" {
			return errors.New("implied-role name is required")
		}
		e.MergeRoleInference(roleInference)
	}

	for _, resourceClass := range spec.ResourceClasses {
		if resourceClass == "" {
			return errors.New("resourceClass name is required")
		}
		e.MergeResourceClass(resourceClass)
	}

	for _, rbacPolicy := range spec.RBACPolicies {
		if rbacPolicy.ObjectType == "" {
			return errors.New("rbac_policy.object_type is required")
		}
		if rbacPolicy.ObjectType != "network" {
			return errors.New("only network rbac_policies are supported")
		}
		if rbacPolicy.ObjectName == "" {
			return errors.New("rbac_policy.object_name is required")
		}
		if rbacPolicy.Action != "access_as_external" && rbacPolicy.Action != "access_as_shared" {
			return errors.New("rbac_policy.action is invalid")
		}
		if rbacPolicy.TargetTenantName == "" {
			return errors.New("rbac_policy.target_tenant_name is required")
		}
		e.MergeRbacPolicy(rbacPolicy)
	}

	return nil
}
