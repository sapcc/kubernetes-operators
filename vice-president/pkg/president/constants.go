/*******************************************************************************
*
* Copyright 2019 SAP SE
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

import "time"

const (
	// CertificateType is exactly that.
	CertificateType = "CERTIFICATE"

	// PrivateKeyType is exactly that.
	PrivateKeyType = "RSA PRIVATE KEY"

	// SecretTLSCertType defines under which key the certificate is stored in the secret.
	// The following cert types will also be considered:
	// (1) with underscore and dot, e.g.: tls_cert || tls.cert
	// (2) *.cert | *.crt
	SecretTLSCertType = "tls.crt"

	// SecretTLSKeyType defines under which key the private key is stored in the secret.
	// The following key types will be checked:
	// (1) with underscore and dot, e.g.: tls_key || tls.key
	SecretTLSKeyType = "tls.key"

	// The vice president is tracking the state of the ingresses it handled via the following annotations.

	// IngressStateEnroll means a enrollment request has to be issued.
	IngressStateEnroll = "enroll"

	// IngressStateRenew means a renewal request has to be be issued.
	IngressStateRenew = "renew"

	// IngressStateApprove means that a certificate has to be approved.
	IngressStateApprove = "approve"

	// IngressStateApproved means that a certificate was approved.
	IngressStateApproved = "approved"

	// IngressStatePickup means that a certificate has to be picked up.
	IngressStatePickup = "pickup"

	// IngressStateReplace means that a certificate has to be replaced.
	IngressStateReplace = "replace"

	// BaseDelay defines the delay after which an ingress is added to the workqueue.
	BaseDelay = 5 * time.Second

	// TmpPath points to tmp directory.
	TmpPath = "/tmp"

	// AnnotationCertificateReplacement triggers one-time replacement of certificates for all hosts defined by the ingress.
	AnnotationCertificateReplacement = "vice-president/replace-cert"

	// AnnotationSecretClaimedByIngress is used to indicate that a secret is being used by another ingress.
	// This prevents multiple ingress' from using the same secret.
	AnnotationSecretClaimedByIngress = "vice-president/claimed-by-ingress"

	// RateLimitPeriod is the period after which all rate limits are reset.
	RateLimitPeriod = 1 * time.Hour

	// IngressFakeCN is the CN of the ingress controllers fake certificate.
	IngressFakeCN = "Kubernetes Ingress Controller Fake Certificate"

	// IngressFakeHost is the list of hosts used by the ingress controllers fake certificate.
	IngressFakeHost = "ingress.local"

	// ReasonSuperseded is the reason for replacing a existing certificate.
	ReasonSuperseded = "SUPERSEDED"

	// UpdateEvent is the type of an update event.
	UpdateEvent = "UpdateCertificate"
)
