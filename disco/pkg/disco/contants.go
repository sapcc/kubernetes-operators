package disco

const (
	// DefaultMetricPort the default port for metrics
	DefaultMetricPort = 9091

	// DefaultIngressAnnotation is the default annotation for an ingress
	DefaultIngressAnnotation = "disco"

	// DefaultRecordsetTTL is the default TTL for a recordset
	DefaultRecordsetTTL = 1800

	// DefaultRecordsetIngressRecord is the default record used for a CNAME
	DefaultRecordsetIngressRecord = "ingress.%s.cloud.sap."

	// DefaultZoneName is the default zone name for a CNAME
	DefaultZoneName = "%s.cloud.sap."

	// DefaultRecheckPeriod in minutes
	DefaultRecheckPeriod = 5

	// DefaultResynPeriod in minutes
	DefaultResyncPeriod = 2

	// DefaultThreadiness in minutes
	DefaultThreadiness = 1
)
