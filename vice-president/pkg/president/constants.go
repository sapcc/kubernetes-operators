/*******************************************************************************
*
* Copyright 2017 SAP SE
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

// CertificateValidityMonth defines how long certificates must be valid before a renewal is invoked (in month)
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
