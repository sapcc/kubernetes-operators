package disco

const (
	// DefaultMetricPort the default port for metrics
	DefaultMetricPort = 9091

	// DefaultIngressAnnotation is the default annotation for an ingress
	DefaultIngressAnnotation = "disco"

	// DefaultRecordsetTTL is the default TTL for a recordset
	DefaultRecordsetTTL = 1800

	// DefaultRecheckPeriod in minutes
	DefaultRecheckPeriod = 5

	// DefaultResyncPeriod in minutes
	DefaultResyncPeriod = 2

	// DefaultThreadiness in minutes
	DefaultThreadiness = 1

	// DiscoFinalizer as seen on the ingress
	DiscoFinalizer = "disco"
)
