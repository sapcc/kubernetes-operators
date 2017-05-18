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
	Region       string `json:"id" yaml:"id"`                                                 // the region id
	Description  string `json:"description,omitempty" yaml:"description,omitempty"`           // the regions description
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
	Name            string                `json:"name" yaml:"name"`                                   // project name
	Description     string                `json:"description,omitempty" yaml:"description,omitempty"` // project description
	Enabled         *bool                 `json:"enabled,omitempty" yaml:"enabled,omitempty"`         // boolean flag to indicate if the project is enabled
	ParentId        string                `json:"parent_id,omitempty" yaml:"parent_id,omitempty"`     // (optional) parent project id
	IsDomain        *bool                 `json:"is_domain,omitempty" yaml:"is_domain,omitempty"`     // is the project actually a domain?
	Endpoints       []ProjectEndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`     // list of project endpoint filters
	RoleAssignments []RoleAssignmentSpec  `json:"roles,omitempty" yaml:"roles,omitempty"`             // list of project-role-assignments
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
			MergeSimpleStructFields(&v, region)
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
			MergeSimpleStructFields(&v, service)
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
				MergeSimpleStructFields(&v, endpoint)
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
			MergeSimpleStructFields(&v, flavor)
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
			MergeSimpleStructFields(&v, domain)
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
				MergeSimpleStructFields(&v, project)
				if len(project.RoleAssignments) > 0 {
					v.MergeRoleAssignments(project)
				}
				if len(project.Endpoints) > 0 {
					v.MergeEndpoint(project)
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
				MergeSimpleStructFields(&v, user)
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
				MergeSimpleStructFields(&v, group)
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
				MergeSimpleStructFields(&v, ra)
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
				MergeSimpleStructFields(&v, ra)
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

func (e *ProjectSpec) MergeEndpoint(project ProjectSpec) {
	if e.Endpoints == nil {
		e.Endpoints = make([]ProjectEndpointSpec, 0)
	}
	for _, ep := range project.Endpoints {
		found := false
		for i, v := range e.Endpoints {
			if v.Region == ep.Region && v.Service == ep.Service {
				glog.V(2).Info("merge project endpoint ", ep)
				MergeSimpleStructFields(&v, ep)
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
				MergeSimpleStructFields(&v, ra)
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
				MergeSimpleStructFields(&v, ra)
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
