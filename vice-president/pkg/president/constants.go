package president

// CertificateValidityMonth defines how long certificates must be valid before a renewal is invoked in month
const CertificateValidityMonth = 1

// CertificateType ..
const CertificateType = "CERTIFICATE"

// PrivateKeyType ..
const PrivateKeyType = "RSA PRIVATE KEY"

// SecretTLSCertType defines under which key the certificate is stored in the secret
// the following cert types will also be considered:
// (1) with underscore and dot, e.g.: tls_cert || tls.cert
// (2) *.cert | *.crt
const SecretTLSCertType = "tls.crt"

// SecretTLSKeyType defines under which key the private key is stored in the secret
// the following key types will be checked:
// (1) with underscore and dot, e.g.: tls_key || tls.key
const SecretTLSKeyType = "tls.key"

// the vice president is tracking the state of the ingresses it handled via the following annotations

// IngressStateAnnotation is the key used to annotate an ingress with the state
const IngressStateAnnotation = "vice-president-state"

// IngressStateEnroll means a enrollment request has to be issued
const IngressStateEnroll = "enroll"

// IngressStateRenew means a renewal request has to be be issued
const IngressStateRenew = "renew"

// IngressStateApprove means that a certificate has to be approved
const IngressStateApprove = "approve"

// IngressStateApproved means that a certificate was approved
const IngressStateApproved = "approved"

// IngressStatePickup means that a certificate has to be picked up
const IngressStatePickup = "pickup"

// IngressTIDAnnotation is the key used to annotate an ingress with the TransactionID (TID)
const IngressTIDAnnotation = "vice-president-tid"