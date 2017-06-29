package president

import (
	"fmt"
)

// Options to configure your vice president
type Options struct {
	KubeConfig          string
	VicePresidentConfig string

	ViceKeyFile string
	ViceCrtFile string

	IngressAnnotation string

	MetricListenAddress string
}

// CheckOptions verifies the Options and sets default values, if necessary
func (o Options) CheckOptions() error {
	if o.ViceCrtFile == "" {
		return fmt.Errorf("Path to vice certificate not provided. Aborting")
	}
	if o.ViceKeyFile == "" {
		return fmt.Errorf("Path to vice key not provided. Aborting")
	}
	if o.VicePresidentConfig == "" {
		return fmt.Errorf("Path to vice config not provided. Aborting")
	}
	if o.KubeConfig == "" {
		LogInfo("Path to kubeconfig not provided. Using Default")
	}
	if o.IngressAnnotation == "" {
		o.IngressAnnotation = "vice-president"
		LogInfo("Ingress annotation not provided. Using default 'vice-president'.")
	}

	if o.MetricListenAddress == "" {
		o.MetricListenAddress = ":9091"
		LogInfo("Metric listen address not provided. Using default :9091.")
	}
	return nil
}
