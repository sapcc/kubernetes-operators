module github.com/sapcc/kubernetes-operators/openstack-seeder

go 1.14

require (
	github.com/ant31/crd-validation v0.0.0-20180801212718-38f6a293f140
	github.com/certifi/gocertifi v0.0.0-20200211180108-c7c1fbc02894 // indirect
	github.com/getsentry/raven-go v0.2.0
	github.com/go-openapi/spec v0.19.3
	github.com/golang/glog v0.0.0-20160126235308-23def4e6c14b
	github.com/spf13/pflag v1.0.5
	gopkg.in/yaml.v2 v2.2.8
	k8s.io/api v0.19.0
	k8s.io/apiextensions-apiserver v0.19.0
	k8s.io/apimachinery v0.19.0
	k8s.io/client-go v0.19.0
	k8s.io/code-generator v0.19.0
	k8s.io/klog/v2 v2.2.0 // indirect
	k8s.io/kube-openapi v0.0.0-20200805222855-6aeccd4b50c6
)

replace (
	k8s.io/api => k8s.io/api v0.0.0-20200821051526-051d027c14e1
	k8s.io/apimachinery => k8s.io/apimachinery v0.0.0-20200821051348-9254095ca5ca
	k8s.io/client-go => k8s.io/client-go v0.0.0-20200821051752-20923fd71b14
	k8s.io/code-generator => k8s.io/code-generator v0.0.0-20200813011144-5a311e69ffcf
)
