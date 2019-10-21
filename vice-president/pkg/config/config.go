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
	"fmt"
	"io/ioutil"

	"gopkg.in/yaml.v1"
)

// VicePresidentConfig is a wrapper for both parts of the config.
type VicePresidentConfig struct {
	ViceConfig `yaml:"vice"`
}

// ViceConfig to define the parameters when talking to the Symantec VICE API.
type ViceConfig struct {
	FirstName          string `yaml:"first_name"`
	LastName           string `yaml:"last_name"`
	EMail              string `yaml:"email"`
	Country            string `yaml:"country"`
	Province           string `yaml:"province"`
	Locality           string `yaml:"locality"`
	Organization       string `yaml:"organization"`
	OrganizationalUnit string `yaml:"organizational_unit"`
	DefaultChallenge   string `yaml:"default_challenge"`
}

// ReadConfig reads a given vice configuration file and returns the ViceConfig object and if applicable an error.
func ReadConfig(filePath string) (cfg VicePresidentConfig, err error) {
	cfgBytes, err := ioutil.ReadFile(filePath)
	if err != nil {
		return cfg, fmt.Errorf("read configuration file: %s", err.Error())
	}
	err = yaml.Unmarshal(cfgBytes, &cfg)
	if err != nil {
		return cfg, fmt.Errorf("parse configuration: %s", err.Error())
	}
	return cfg, nil
}
