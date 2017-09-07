/*******************************************************************************
*
* Copyright 2017 SAP SE
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
	"encoding/base64"
	"bytes"
)

func base64DecodePEM(encodedPEM []byte) ([]byte, int, error) {
	encodedPEM = bytes.Trim(encodedPEM,"\"")
	decodedPEM := make([]byte, base64.StdEncoding.DecodedLen(len(encodedPEM)))
	l, err := base64.StdEncoding.Decode(decodedPEM, encodedPEM)
	if err != nil {
		return nil, 0, err
	}
	return decodedPEM, l, nil
}
