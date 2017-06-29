# Vice President

This operator automatically requests and renews certificates for Kubernetes
Ingress resources using the Symantec Vice API.

## Features

  - Automatically requests Certificates via Symantec API
  - Periodically and automatically detects expirations and renews certificates
  - Required certificates are discovered via Kubernetes API

## Requirements

  - go1.8.3

## Usage

The vice president requires the following configuration and certificates:

```
Usage of vice-president:
      --kubeconfig 			string	Path to kubeconfig file with authorization and master location information. Optional if vice president is deployed in a cluster.
      --vice-config 		string	Path to VICE config file with certificate parameters.
      --vice-cert 			string	A PEM encoded certificate file.
      --vice-key 			string	A PEM encoded private key file.
      --ingress-annotation 	string	Only an ingress with this annotation will be considered. (default: { "vice-president": true } )
```
Note that Ingresses without the previously described annotation are ignored.

## Notes on the implementation 

The vice president discovers ingresses in the cluster via the Kubernetes API.
An ingress can reference a secret in its spec's TLS section.
The secret contains the certificates, of which the vice president takes care.

To keep track of the current state of the certificates, the corresponding ingress is annotated with the current state and, 
if available, the Transaction ID (TID) returned by the Symantec VICE API.
