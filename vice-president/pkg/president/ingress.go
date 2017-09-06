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
	"fmt"
	"strings"

	"k8s.io/client-go/pkg/api"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
)

// SetIngressStateAndTIDForHost annotates an ingress with state and TID for a host
func (vp *Operator) SetIngressStateAndTIDForHost(ingress *v1beta1.Ingress, host, state, tid string) {
	updatedIngress, err := ingressSetAnnotations(
		ingress,
		map[string]string{
			fmt.Sprintf("%s/%s", host, IngressStateAnnotation): state,
			fmt.Sprintf("%s/%s", host, IngressTIDAnnotation):   tid,
		})

	if checkError(err) != nil {
		LogError(err.Error())
		return
	}
	vp.updateUpstreamIngress(updatedIngress, ingress)
}

// SetIngressStateForHost annotates and ingress with the state for a host
func (vp *Operator) SetIngressStateForHost(ingress *v1beta1.Ingress, host, state string) {
	updatedIngress, err := ingressSetAnnotations(
		ingress,
		map[string]string{
			fmt.Sprintf("%s/%s", host, IngressStateAnnotation): state,
		},
	)
	if checkError(err) != nil {
		LogError(err.Error())
		return
	}
	vp.updateUpstreamIngress(updatedIngress, ingress)
}

// SetIngressTIDForHost annotates an ingress with the TID for a host
func (vp *Operator) SetIngressTIDForHost(ingress *v1beta1.Ingress, host, tid string) {
	updatedIngress, err := ingressSetAnnotations(
		ingress,
		map[string]string{
			fmt.Sprintf("%s/%s", host, IngressTIDAnnotation): tid,
		},
	)
	if checkError(err) != nil {
		LogError(err.Error())
		return
	}
	vp.updateUpstreamIngress(updatedIngress, ingress)
}

// GetIngressStateForHost returns the state for a host
func (vp *Operator) GetIngressStateForHost(ingress *v1beta1.Ingress, host string) string {
	return getIngressAnnotationForHost(ingress, host, IngressStateAnnotation)
}

// GetIngressTIDForHost returns the TID for a host
func (vp *Operator) GetIngressTIDForHost(ingress *v1beta1.Ingress, host string) string {
	return getIngressAnnotationForHost(ingress, host, IngressTIDAnnotation)
}

func (vp *Operator) ClearIngressStateForHost(ingress *v1beta1.Ingress, host string) {
  LogInfo("Removing state and TID annotation from ingress %s/%s for host %s", ingress.GetNamespace(), ingress.GetName(), host)

  if ingress.GetAnnotations() == nil {
    return
  }

  o, err := api.Scheme.Copy(ingress)
  if err != nil {
    return
  }
  updatedIngress := o.(*v1beta1.Ingress)

  annotations := updatedIngress.GetAnnotations()
  delete(annotations, fmt.Sprintf("%s/%s", host, IngressStateAnnotation))
  updatedIngress.SetAnnotations(annotations)

  vp.updateUpstreamIngress(updatedIngress, ingress)
}

func getIngressAnnotationForHost(ingress *v1beta1.Ingress, host, annotationKey string) string {
	for k, v := range ingress.GetAnnotations() {
		if strings.Contains(k, annotationKey) && strings.Contains(k, host) {
			return v
		}
	}
	return ""
}

func ingressSetAnnotations(ingress *v1beta1.Ingress, annotations map[string]string) (*v1beta1.Ingress, error) {
	o, err := api.Scheme.Copy(ingress)
	if err != nil {
		return nil, err
	}
	updatedIngress := o.(*v1beta1.Ingress)
	anno := updatedIngress.GetAnnotations()
	if anno == nil {
		anno = map[string]string{}
	}

	for k, v := range annotations {
		LogInfo("Annotating ingress %s/%s with %s : %s", ingress.GetNamespace(), ingress.GetName(), k, v)
		anno[k] = v
	}

	updatedIngress.SetAnnotations(anno)

	return updatedIngress, nil
}
