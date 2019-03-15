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
	"io/ioutil"
	"os"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v1"
)

// Config ...
type Config struct {
	AuthOpts `yaml:",inline"`
}

// ReadConfig reads a given configuration file and returns the ViceConfig object and if applicable an error.
func ReadConfig(filePath string) (*Config, error) {
	cfg := Config{}
	cfgBytes, err := ioutil.ReadFile(filePath)
	if err != nil {
		return nil, errors.Wrap(err, "could not read configuration file")
	}
	err = yaml.Unmarshal(cfgBytes, &cfg)
	if err != nil {
		return nil, errors.Wrap(err, "could not parse configuration")
	}

	if err := cfg.checkConfig(); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func (c *Config) checkConfig() error {
	errs := make([]string, 0)
	if c.AuthURL == "" {
		errs = append(errs, "OS_AUTH_URL")
	}
	if c.Username == "" {
		errs = append(errs, "OS_USERNAME")
	}
	if c.UserDomainName == "" {
		errs = append(errs, "OS_USER_DOMAIN_NAME")
	}
	if c.RegionName == "" {
		errs = append(errs, "OS_REGION_NAME")
	}
	if c.ProjectName == "" {
		errs = append(errs, "OS_PROJECT_NAME")
	}
	if c.ProjectDomainName == "" {
		errs = append(errs, "OS_PROJECT_DOMAIN_NAME")
	}

	// Allow providing OS_PASSWORD via environment.
	if c.Password == "" {
		p := os.Getenv("OS_PASSWORD")
		if p != "" {
			c.Password = p
		} else {
			errs = append(errs, "OS_PASSWORD")
		}
	}

	if len(errs) > 0 {
		return errors.New("missing " + strings.Join(errs, ", "))
	}
	return nil
}
