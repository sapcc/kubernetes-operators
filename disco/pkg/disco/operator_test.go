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
	"testing"

	"github.com/stretchr/testify/suite"
	"k8s.io/api/extensions/v1beta1"
	"k8s.io/apimachinery/pkg/apis/meta/v1"
)

type TestSuite struct {
	suite.Suite

	Disco *Operator
}

func (s *TestSuite) SetupSuite() {
	opts := Options{
		ConfigPath:        "fixtures/example.discoconfig",
		KubeConfig:        "fixtures/example.kubeconfig",
		Record:            "ingress.foobar.tld.",
		ZoneName:          "foobar.tld.",
		IngressAnnotation: DefaultIngressAnnotation,
	}
	s.Disco = &Operator{
		Options: opts,
	}
}

func TestMySuite(t *testing.T) {
	suite.Run(t, new(TestSuite))
}

func (s *TestSuite) TestIngressDiscoAnnotation() {
	stimuli := map[*v1beta1.Ingress]bool{
		&v1beta1.Ingress{
			ObjectMeta: v1.ObjectMeta{
				Name:        "ignoreMe",
				Namespace:   "default",
				Annotations: map[string]string{},
			},
		}: false,
		&v1beta1.Ingress{
			ObjectMeta: v1.ObjectMeta{
				Name:      "takeOnMe",
				Namespace: "default",
				Annotations: map[string]string{
					"disco": "true",
				},
			},
		}: true,
	}

	for ing, expectedBool := range stimuli {
		s.Assert().Equal(s.Disco.isTakeCareOfIngress(ing), expectedBool)
	}
}
