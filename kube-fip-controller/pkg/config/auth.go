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

package config

import (
	"io/ioutil"
	"os"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

// Auth used for OpenStack authentication parameters.
type Auth struct {
	AuthURL           string `yaml:"auth_url"`
	RegionName        string `yaml:"region_name"`
	Username          string `yaml:"username"`
	UserDomainName    string `yaml:"user_domain_name"`
	Password          string `yaml:"password"`
	ProjectName       string `yaml:"project_name"`
	ProjectDomainName string `yaml:"project_domain_name"`
}

// ReadAuthConfig reads a given configuration file and returns the ViceConfig object and if applicable an error.
func ReadAuthConfig(filePath string) (*Auth, error) {
	cfgBytes, err := ioutil.ReadFile(filePath)
	if err != nil {
		return nil, errors.Wrap(err, "could not read configuration file")
	}

	var tmp struct {
		Auth `yaml:",inline"`
	}
	err = yaml.Unmarshal(cfgBytes, &tmp)
	if err != nil {
		return nil, errors.Wrap(err, "could not parse configuration")
	}

	err = tmp.Auth.verify()
	return &tmp.Auth, err
}

func (a *Auth) verify() error {
	errs := make([]string, 0)
	if a.AuthURL == "" {
		errs = append(errs, "OS_AUTH_URL")
	}
	if a.Username == "" {
		errs = append(errs, "OS_USERNAME")
	}
	if a.UserDomainName == "" {
		errs = append(errs, "OS_USER_DOMAIN_NAME")
	}
	if a.RegionName == "" {
		errs = append(errs, "OS_REGION_NAME")
	}
	if a.ProjectName == "" {
		errs = append(errs, "OS_PROJECT_NAME")
	}
	if a.ProjectDomainName == "" {
		errs = append(errs, "OS_PROJECT_DOMAIN_NAME")
	}

	// Allow providing OS_PASSWORD via environment.
	if a.Password == "" {
		p := os.Getenv("OS_PASSWORD")
		if p != "" {
			a.Password = p
		} else {
			errs = append(errs, "OS_PASSWORD")
		}
	}

	if len(errs) > 0 {
		return errors.New("missing " + strings.Join(errs, ", "))
	}
	return nil
}
