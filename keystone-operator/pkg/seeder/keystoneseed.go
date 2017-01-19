package seeder

import (
	"encoding/json"
	"errors"
	"fmt"
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

type KeystoneSeed struct {
	unversioned.TypeMeta `json:",inline"`
	Metadata             api.ObjectMeta `json:"metadata"`
	VisitedDependencies  map[string]bool
	Spec                 KeystoneSeedSpec `json:"spec" yaml:"spec"`
}

type KeystoneSeedList struct {
	unversioned.TypeMeta `json:",inline"`
	Metadata             unversioned.ListMeta `json:"metadata"`

	Items []KeystoneSeed `json:"items" yaml:"items"`
}

type KeystoneSeedSpec struct {
	Dependencies []string      `json:"dependencies,omitempty" yaml:"dependencies,omitempty"`
	Roles        []string      `json:"roles,omitempty" yaml:"roles,omitempty"`
	Regions      []RegionSpec  `json:"regions,omitempty" yaml:"regions,omitempty"`
	Services     []ServiceSpec `json:"services,omitempty" yaml:"services,omitempty"`
	Domains      []DomainSpec  `json:"domains,omitempty" yaml:"domains,omitempty"`
}

type RegionSpec struct {
	Region       string `json:"id" yaml:"id"`
	Description  string `json:"description,omitempty" yaml:"description,omitempty"`
	ParentRegion string `json:"parent_region_id,omitempty" yaml:"parent_region_id,omitempty"`
}

type ServiceSpec struct {
	Name        string         `json:"name" yaml:"name"`
	Type        string         `json:"type" yaml:"type"`
	Description string         `json:"description,omitempty" yaml:"description,omitempty"`
	Enabled     *bool          `json:"enabled,omitempty" yaml:"enabled,omitempty"`
	Endpoints   []EndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`
}

type EndpointSpec struct {
	Region    string `json:"region" yaml:"region"`
	Interface string `json:"interface" yaml:"interface"`
	URL       string `json:"url" yaml:"url"`
	Enabled   *bool  `json:"enabled,omitempty" yaml:"enabled,omitempty"`
}

type DomainSpec struct {
	Name            string               `json:"name" yaml:"name"`
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"`
	Enabled         *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`
	Users           []UserSpec           `json:"users,omitempty" yaml:"users,omitempty"`
	Groups          []GroupSpec          `json:"groups,omitempty" yaml:"groups,omitempty"`
	Projects        []ProjectSpec        `json:"projects,omitempty" yaml:"projects,omitempty"`
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`
	Config          DomainConfigSpec     `json:"config,omitempty" yaml:"config,omitempty"`
}

type DomainConfigSpec struct {
	IdentityConfig map[string]string      `json:"identity,omitempty" yaml:"identity,omitempty"`
	LdapConfig     map[string]interface{} `json:"ldap,omitempty" yaml:"ldap,omitempty"`
	CCAdConfig     map[string]interface{} `json:"cc_ad,omitempty" yaml:"cc_ad,omitempty"`
}

type ProjectSpec struct {
	Name            string                `json:"name" yaml:"name"`
	Description     string                `json:"description,omitempty" yaml:"description,omitempty"`
	Enabled         *bool                 `json:"enabled,omitempty" yaml:"enabled,omitempty"`
	ParentId        string                `json:"parent_id,omitempty" yaml:"parent_id,omitempty"`
	IsDomain        *bool                 `json:"is_domain,omitempty" yaml:"is_domain,omitempty"`
	Endpoints       []ProjectEndpointSpec `json:"endpoints,omitempty" yaml:"endpoints,omitempty"`
	RoleAssignments []RoleAssignmentSpec  `json:"roles,omitempty" yaml:"roles,omitempty"`
}

type ProjectEndpointSpec struct {
	Region  string `json:"region" yaml:"region"`
	Service string `json:"service" yaml:"service"`
}

type RoleAssignmentSpec struct {
	Role      string `json:"role" yaml:"role"`
	Domain    string `json:"domain,omitempty" yaml:"domain,omitempty"`
	Project   string `json:"project,omitempty" yaml:"project,omitempty"`
	Group     string `json:"group,omitempty" yaml:"group,omitempty"`
	User      string `json:"user,omitempty" yaml:"user,omitempty"`
	Inherited *bool  `json:"inherited,omitempty" yaml:"inherited,omitempty"`
}

type UserSpec struct {
	Name            string               `json:"name" yaml:"name"`
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"`
	Password        string               `json:"password,omitempty" yaml:"password,omitempty"`
	Enabled         *bool                `json:"enabled,omitempty" yaml:"enabled,omitempty"`
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`
}

type GroupSpec struct {
	Name            string               `json:"name" yaml:"name"`
	Description     string               `json:"description,omitempty" yaml:"description,omitempty"`
	Users           []string             `json:"users,omitempty" yaml:"users,omitempty"`
	RoleAssignments []RoleAssignmentSpec `json:"roles,omitempty" yaml:"roles,omitempty"`
}

func (e *KeystoneSeedSpec) MergeRole(role string) {
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

func (e *KeystoneSeedSpec) MergeRegion(region RegionSpec) {
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

func (e *KeystoneSeedSpec) MergeService(service ServiceSpec) {
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

func (e *KeystoneSeedSpec) MergeDomain(domain DomainSpec) {
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
		for i, v := range e.Users {
			if v == user {
				glog.V(2).Info("merge group user ", user)
				MergeSimpleStructFields(&v, user)
				e.Users[i] = v
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

func NewKeystoneSeedClientForConfig(c *rest.Config) (*rest.RESTClient, error) {
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
				&KeystoneSeed{},
				&KeystoneSeedList{},
				&api.ListOptions{},
				&api.DeleteOptions{},
			)
			return nil
		})
	schemeBuilder.AddToScheme(api.Scheme)

	return rest.RESTClientFor(c)
}

func EnsureKeystoneSeedThirdPartyResource(client *kubernetes.Clientset) error {
	const name = "keystone-seed.openstack.stable.sap.cc"

	_, err := client.Extensions().ThirdPartyResources().Get(name)
	if err != nil {
		// The resource doesn't exist, so we create it.
		newResource := v1beta1.ThirdPartyResource{
			ObjectMeta: v1.ObjectMeta{
				Name: name,
			},
			Description: "A specification of an openstack keystone seed",
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

func (e *KeystoneSeedSpec) MergeSpec(spec KeystoneSeedSpec) error {
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
	return nil
}

// The code below is used only to work around a known problem with third-party
// resources and ugorji. If/when these issues are resolved, the code below
// should no longer be required.
//

func (s *KeystoneSeed) GetObjectKind() unversioned.ObjectKind {
	return &s.TypeMeta
}

func (s *KeystoneSeed) GetObjectMeta() meta.Object {
	return &s.Metadata
}

func (sl *KeystoneSeedList) GetObjectKind() unversioned.ObjectKind {
	return &sl.TypeMeta
}

func (sl *KeystoneSeedList) GetListMeta() unversioned.List {
	return &sl.Metadata
}

type KeystoneSeedListCopy KeystoneSeedList
type KeystoneSeedCopy KeystoneSeed

func (e *KeystoneSeed) UnmarshalJSON(data []byte) error {
	tmp := KeystoneSeedCopy{}
	err := json.Unmarshal(data, &tmp)
	if err != nil {
		glog.Errorf("spec %s is invalid: %s", tmp.Metadata.Name, err)
		return nil
	}
	tmp2 := KeystoneSeed(tmp)
	*e = tmp2
	return nil
}

func (el *KeystoneSeedList) UnmarshalJSON(data []byte) error {
	tmp := KeystoneSeedListCopy{}
	err := json.Unmarshal(data, &tmp)
	if err != nil {
		glog.Errorf("ERROR: invalid KeystoneSeedList: %s", err)
		return nil
	}
	tmp2 := KeystoneSeedList(tmp)
	*el = tmp2
	return nil
}
