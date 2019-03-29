package disco

const (
	// DefaultMetricPort the default port for metrics.
	DefaultMetricPort = 9091

	// DefaultIngressAnnotation is the default annotation for an ingress.
	DefaultIngressAnnotation = "disco"

	// DefaultRecordsetTTL is the default TTL for a recordset.
	DefaultRecordsetTTL = 1800

	// DiscoRecordDescription is the default description for a recordset.
	DiscoRecordsetDescription = "Managed by the DISCOperator."

	// DefaultRecheckPeriod in minutes.
	DefaultRecheckPeriod = 5

	// DefaultResyncPeriod in minutes.
	DefaultResyncPeriod = 2

	// DefaultThreadiness in minutes.
	DefaultThreadiness = 1

	// DiscoFinalizer as seen on the ingress.
	DiscoFinalizer = "disco.extensions/v1beta1"

	// DiscoAnnotationRecord allows setting a different record than the default per ingress.
	DiscoAnnotationRecord = "disco/record"

	// DiscoAnnotationRecordType allows setting the record type. Must be CNAME, A, NS, SOA. Default: CNAME.
	DiscoAnnotationRecordType = "disco/record-type"

	// DiscoAnnotationRecordDescription allows setting the records description.
	DiscoAnnotationRecordDescription = "disco/record-description"

	// CreateEvent is the type of an creation event.
	CreateEvent = "CreateRecordset"

	// UpdateEvent is the type of an update event.
	UpdateEvent = "UpdateRecordset"

	// DeleteEvent is the type of an deletion event.
	DeleteEvent = "DeleteRecordset"

	// EventComponent describes the component emitting an event.
	EventComponent = "disco"
)
