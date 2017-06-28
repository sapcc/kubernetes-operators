package regions

type CertificateRequest struct {
	CN   string
	SANS []string
}

var NL []CertificateRequest = []CertificateRequest{
	CertificateRequest{"baremetal-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"compute-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"compute-console-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"horizon-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"dns-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"identity.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"identity-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"identity-admin-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"image-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"keymanager-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"network-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"volume-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"share-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"objectstore-3.eu-nl-1.cloud.sap", []string{"objectstore-3.eu-nl-1.cloud.sap", "repo.eu-nl-1.cloud.sap" /* "*.objectstore-3.eu-nl-1.cloud.sap" , "*.content.eu-nl-1.cloud.sap" */}},
	CertificateRequest{"objectstore-4.eu-nl-1.cloud.sap", []string{"objectstore-4.eu-nl-1.cloud.sap" /* "*.objectstore-4.eu-nl-1.cloud.sap" */}},
	CertificateRequest{"arc-pki.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"arc.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"alpha.arc.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"beta.arc.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"stable.arc.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"automation.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"dashboard.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"lyra.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"limes-3.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"limes-4.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"grafana.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"logs.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"monitoring.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"prometheus.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"prometheus-collector.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"sentry.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"rally.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"monasca-elasticsearch-manager.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"monasca-elasticsearch.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"monasca-kafka-manager.eu-nl-1.cloud.sap", []string{}},
	CertificateRequest{"monasca-logging.eu-nl-1.cloud.sap", []string{}},
}
