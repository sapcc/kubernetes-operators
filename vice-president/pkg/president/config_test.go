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

package president

import (
	"path"
)

func (s *TestSuite) TestLoadConfig() {
	config, err := ReadConfig(path.Join(FIXTURES, "example.vicepresidentconfig"))

	s.NoError(err, "there should be no error reading the configuration")
	s.Equal("Max", config.FirstName)
	s.Equal("Muster", config.LastName)
}
