module github.com/sapcc/kubernetes-operators/externalip

go 1.23.1

require (
	github.com/golang/glog v1.2.2
	github.com/spf13/pflag v1.0.5
	k8s.io/api v0.31.0
	k8s.io/apimachinery v0.31.0
	k8s.io/client-go v0.31.0
)

require (
	github.com/davecgh/go-spew v1.1.2-0.20180830191138-d8f796af33cc // indirect
	github.com/emicklei/go-restful/v3 v3.12.0 // indirect
	github.com/fxamacker/cbor/v2 v2.7.0 // indirect
	github.com/go-logr/logr v1.4.2 // indirect
	github.com/go-openapi/jsonpointer v0.21.0 // indirect
	github.com/go-openapi/jsonreference v0.21.0 // indirect
	github.com/go-openapi/swag v0.23.0 // indirect
	github.com/gogo/protobuf v1.3.2 // indirect
	github.com/golang/protobuf v1.5.4 // indirect
	github.com/google/gnostic-models v0.6.9-0.20230804172637-c7be7c783f49 // indirect
	github.com/google/go-cmp v0.6.0 // indirect
	github.com/google/gofuzz v1.2.0 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/imdario/mergo v0.3.16 // indirect
	github.com/josharian/intern v1.0.0 // indirect
	github.com/json-iterator/go v1.1.12 // indirect
	github.com/mailru/easyjson v0.7.7 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
	github.com/munnerz/goautoneg v0.0.0-20191010083416-a7dc8b61c822 // indirect
	github.com/x448/float16 v0.8.4 // indirect
	golang.org/x/net v0.26.0 // indirect
	golang.org/x/oauth2 v0.21.0 // indirect
	golang.org/x/sys v0.21.0 // indirect
	golang.org/x/term v0.21.0 // indirect
	golang.org/x/text v0.16.0 // indirect
	golang.org/x/time v0.5.0 // indirect
	google.golang.org/protobuf v1.34.2 // indirect
	gopkg.in/inf.v0 v0.9.1 // indirect
	gopkg.in/yaml.v2 v2.4.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
	k8s.io/klog/v2 v2.130.1 // indirect
	k8s.io/kube-openapi v0.0.0-20240411171206-dc4e619f62f3 // indirect
	k8s.io/utils v0.0.0-20240711033017-18e509b52bc8 // indirect
	sigs.k8s.io/json v0.0.0-20221116044647-bc3834ca7abd // indirect
	sigs.k8s.io/structured-merge-diff/v4 v4.4.1 // indirect
	sigs.k8s.io/yaml v1.4.0 // indirect
)

replace (
	k8s.io/api => k8s.io/api v0.31.0
	k8s.io/apiextensions-apiserver => k8s.io/apiextensions-apiserver v0.31.0
	k8s.io/apimachinery => k8s.io/apimachinery v0.31.0
	k8s.io/apiserver => k8s.io/apiserver v0.31.0
	k8s.io/cli-runtime => k8s.io/cli-runtime v0.31.0
	k8s.io/client-go => k8s.io/client-go v0.31.0
	k8s.io/cloud-provider => k8s.io/cloud-provider v0.31.0
	k8s.io/cluster-bootstrap => k8s.io/cluster-bootstrap v0.31.0
	k8s.io/code-generator => k8s.io/code-generator v0.31.0
	k8s.io/component-base => k8s.io/component-base v0.31.0
	k8s.io/component-helpers => k8s.io/component-helpers v0.32.0
	k8s.io/controller-manager => k8s.io/controller-manager v0.31.0
	k8s.io/cri-api => k8s.io/cri-api v0.31.0
	k8s.io/csi-translation-lib => k8s.io/csi-translation-lib v0.31.0
	k8s.io/kube-aggregator => k8s.io/kube-aggregator v0.31.0
	k8s.io/kube-controller-manager => k8s.io/kube-controller-manager v0.31.0
	k8s.io/kube-proxy => k8s.io/kube-proxy v0.31.0
	k8s.io/kube-scheduler => k8s.io/kube-scheduler v0.31.0
	k8s.io/kubectl => k8s.io/kubectl v0.31.0
	k8s.io/kubelet => k8s.io/kubelet v0.31.0
	k8s.io/kubernetes/pkg/util/dbus => k8s.io/kubernetes/pkg/util/dbus v0.31.0
	k8s.io/legacy-cloud-providers => k8s.io/legacy-cloud-providers v0.31.0
	k8s.io/metrics => k8s.io/metrics v0.31.0
	k8s.io/mount-utils => k8s.io/mount-utils v0.31.0
	k8s.io/pod-security-admission => k8s.io/pod-security-admission v0.31.0
	k8s.io/sample-apiserver => k8s.io/sample-apiserver v0.31.0
)
