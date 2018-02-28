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

package fusion

import (
	"github.com/pkg/errors"
	"github.com/prometheus/prometheus/pkg/rulefmt"
	"gopkg.in/yaml.v2"
)

func validateRules(rules map[string]string) (err error) {
	defer func() {
		if recover() != nil {
			err = errors.Wrap(err, "panic while parsing and validating rules")
			return
		}
	}()

	for k, v := range rules {
		LogInfo("validating rules %s", k)
		rgs, err := parseRules([]byte(v))
		if err != nil {
			return err
		}
		errs := rgs.Validate()
		for _, e := range errs {
			err = errors.Wrap(e, "failed to validate rules")
		}
	}
	return nil
}

func parseRules(content []byte) (rgs *rulefmt.RuleGroups, err error) {
	var groups rulefmt.RuleGroups
	if err := yaml.Unmarshal(content, &groups); err != nil {
		return nil, err
	}
	return &groups, err
}

func containsRules(dst, src map[string]string) bool {
	for k, v := range src {
		if dst[k] == v {
			return true
		}
	}
	return false
}

func mapContains(m map[string]string, search string) bool {
	for k := range m {
		if k == search {
			return true
		}
	}
	return false
}

func ruleOrAlertGroupContains(rg []rulefmt.Rule, rule rulefmt.Rule) bool {
	name := rule.Record
	if name == "" {
		name = rule.Alert
	}

  for _, rule := range rg {
    if rule.Record == name || rule.Alert == name {
      return true
    }
  }
  return false
}

func fuseMaps(dstMap, srcMap map[string]string) (errs []error) {
	for srcK, srcV := range srcMap {
		// key does not exist -> just add
		if !mapContains(dstMap, srcK) {
			dstMap[srcK] = srcV
		// key exists -> merge rules
		} else {
			sRg, err := parseRules([]byte(srcV))
			if err != nil {
				errs = append(errs, err)
				return
			}
			dRg, err := parseRules([]byte(dstMap[srcK]))
			if err != nil {
				errs = append(errs, err)
				return
			}
			if e := fuseRuleGroups(dRg,sRg); e != nil {
				errs = append(errs, e...)
				return
			}
			result, err := ruleGroupsToString(*dRg)
			if err != nil {
				errs = append(errs, err)
			}
			dstMap[srcK] = result
		}
	}
	return
}

func fuseRuleGroups(dst, src *rulefmt.RuleGroups) (errs []error) {
	for _, srg := range src.Groups {
		for k, drg := range dst.Groups {
			// if there's a rulegroup with the same name merge non-conflicting, valid rules
			if srg.Name == drg.Name {
				for _, rule := range srg.Rules {
					if e := rule.Validate(); e != nil {
						LogInfo("not adding to rulegroup %s, due to invalid rule: %s", drg.Name, rule.Record)
						errs = append(errs, e...)
					} else {
            rg := dst.Groups[k].Rules
					  if !ruleOrAlertGroupContains(rg, rule) {
              LogDebug("adding to rulegroup %s: rule %s", drg.Name, rule.Record)
              dst.Groups[k].Rules = append(drg.Rules, rule)
            }
					}
				}
				// add if no rulegroup with this name just append
			} else {
				LogDebug("adding rulegroup %s", srg.Name)
				dst.Groups = append(dst.Groups, srg)
			}
		}
	}
	return
}

// ruleGroupsToString returns the yaml string
func ruleGroupsToString(rg rulefmt.RuleGroups) (string, error) {
	out, err := yaml.Marshal(&rg)
	if err != nil {
		return "", err
	}
	return string(out), nil
}
