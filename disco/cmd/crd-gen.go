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

package main

import (
	"fmt"
	"os"

	crdutils "github.com/ant31/crd-validation/pkg"
	"github.com/sapcc/kubernetes-operators/disco/pkg/k8sutils"
)

func main() {
	crd := k8sutils.NewDiscoRecordCRD()
	if err := crdutils.MarshallCrd(crd, "yaml"); err != nil {
		fmt.Println("Error: ", err)
		os.Exit(1)
	}
	os.Exit(0)
}
