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
	"errors"
	"fmt"
	"io/ioutil"
	"strings"

	yaml "gopkg.in/yaml.v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

// Config to define the parameters when talking to the Symantec VICE API
type Config struct {
	AuthOpts `yaml:"auth"`
}

// ReadConfig reads a given configuration file and returns the ViceConfig object and if applicable an error
func ReadConfig(filePath string) (cfg Config, err error) {
	cfgBytes, err := ioutil.ReadFile(filePath)
	if err != nil {
		return cfg, fmt.Errorf("read configuration file: %s", err.Error())
	}
	err = yaml.Unmarshal(cfgBytes, &cfg)
	if err != nil {
		return cfg, fmt.Errorf("parse configuration: %s", err.Error())
	}
	return cfg, cfg.checkConfig()
}

func newClientConfig(options Options) *rest.Config {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}
	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}
	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		LogFatal("Couldn't get Kubernetes default config: %s", err)
	}
	return config
}

func (c *Config) checkConfig() error {
	errs := []string{}
	if c.AuthURL == "" {
		errs = append(errs, "OS_AUTH_URL")
	}
	if c.Username == "" {
		errs = append(errs, "OS_USERNAME")
	}
	if c.UserDomainName == "" {
		errs = append(errs, "OS_USER_DOMAIN_NAME")
	}
	if c.Password == "" {
		errs = append(errs, "OS_PASSWORD")
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
	if len(errs) > 0 {
		return errors.New("missing "+strings.Join(errs, ", "))
	}
	return nil
}
