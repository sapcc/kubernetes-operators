module github.com/sapcc/kubernetes-operators/openstack-seeder

go 1.14

require (
	github.com/certifi/gocertifi v0.0.0-20200211180108-c7c1fbc02894 // indirect
	github.com/getsentry/raven-go v0.2.0
	github.com/go-openapi/spec v0.19.5
	github.com/golang/glog v0.0.0-20160126235308-23def4e6c14b
	github.com/spf13/pflag v1.0.5
	gopkg.in/yaml.v2 v2.4.0
	k8s.io/api v0.21.0
	k8s.io/apiextensions-apiserver v0.21.0
	k8s.io/apimachinery v0.21.0
	k8s.io/client-go v0.21.0
	k8s.io/code-generator v0.21.0
	k8s.io/kube-openapi v0.0.0-20210305001622-591a79e4bda7
)

replace (
	k8s.io/api => k8s.io/api v0.0.0-20200821051526-051d027c14e1
	k8s.io/apimachinery => k8s.io/apimachinery v0.0.0-20200821051348-9254095ca5ca
	k8s.io/client-go => k8s.io/client-go v0.0.0-20200821051752-20923fd71b14
	k8s.io/code-generator => k8s.io/code-generator v0.0.0-20200813011144-5a311e69ffcf
)
