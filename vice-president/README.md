# Vice President

[![Docker Repository](https://img.shields.io/docker/pulls/sapcc/vice-president.svg?maxAge=604800)](https://hub.docker.com/r/sapcc/vice-president/)

This operator automatically checks, requests and renews certificates for Kubernetes Ingresses using the Symantec Vice API.

An ingress is a resource in Kubernetes that comprises a set of rules, which allow routing inbound traffic to cluster services.
Find more details in the [official documentation](https://kubernetes.io/docs/concepts/services-networking/ingress/#what-is-ingress).

The vice president discovers the ingresses in a cluster by continuously watching the Kubernetes API. 
When it comes to TLS, an ingress can reference a secret in it's spec TLS section. 
This secret contains the certificate and the private key, of which the vice president will take care.

The operator exposes prometheus metrics on successful or failed enrollments, renewals, approvals or pickups, 
which can be useful in case of an error.

## Features

  - Discovers required certificates via Kubernetes API .
  - Automatically requests Certificates via Symantec API.
  - Periodically verifies Certificates.
  - Automatically renews certificates that would expire within a configurable duration.
  - Exposes Prometheus metrics.
  - Creates Kubernetes events for successful, failed certificate creations.

## Requirements

  - go1.8.3

## Usage

A [helm chart](https://github.com/sapcc/helm-charts/tree/master/system/kube-system/charts/vice-president/) can be used to bring the vice president to your cluster.  
Note that the vice president considers only ingresses that are annotated with 
```
metadata:
  annotations:
    vice-president: "true"
```
Other ingresses are ignored. See [example ingress](./example/vice-presidential-ingress.yaml).

The following configuration and certificates are required.  
An example VICE configuration can be found [here](./etc/vice-president/vice-president.conf). 

```
Usage of vice-president:
      --ca-cert string                          A PEM encoded root CA certificate. (optional. will attempt to download if not found) (default "/etc/vice-president/secrets/ca.cert")
      --certificate-recheck-interval duration   Interval for checking certificates. (default 5m0s)
      --debug                                   Enable debug logging.
      --enable-symantec-metrics                 Export additional symantec metrics.
      --enable-validate-remote-cert             Enable validation of remote certificate via TLS handshake.
      --intermediate-cert string                A PEM encoded intermediate certificate. (default "/etc/vice-president/secrets/intermediate.cert")
      --kubeconfig string                       Path to kubeconfig file with authorization and master location information.
      --metric-port int                         Port on which Prometheus metrics are exposed. (default 9091)
      --min-cert-validity-days int              Renew certificates that expire within n days. (default 30)
      --rate-limit int                          Rate limit of certificate enrollments per host. (unlimited: -1) (default 2)
      --resync-interval duration                Interval for resyncing informers. (default 2m0s)
      --threadiness int                         Operator threadiness. (default 10)
  -v, --v Level                                 log level for V logs
      --vice-cert string                        A PEM encoded certificate file. (default "/etc/vice-president/secrets/vice.cert")
```

Moreover the operator stores the TLS key and certificate in the secret using the following format:
```
...
data:
  tls.crt: < x509.Certificate >
  tls.key: < rsa.PrivateKey >
```
The keys `tls.crt`,`tls.key` can be adjusted by setting an annotation. Example:
```
metadata:
  annotations:
    vice-president/tls-cert-secret-key: "ssl.cert"
    vice-president/tls-key-secret-key:  "ssl.key"
```

Setting the annotation `vice-president/replace-cert: "true"` will immediately trigger the replacement of the certificate, 
which might be helpful while switching from Symantec to Digicert CA.  

## Development

The vice president uses [dep](https://github.com/golang/dep) to manage its dependencies. 
Run `make vendor` to install them.

## Debug

The vice president provides the following set of metrics, which can be useful for alerting or debugging:  
  `vice_president_successful_enrollments`  
  `vice_president_failed_enrollments`  
  `vice_president_successful_renewals`   
  `vice_president_failed_renewals`   
  `vice_president_successful_approvals`   
  `vice_president_failed_approvals`     
  `vice_president_successful_pickups`    
  `vice_president_failed_pickups`   

Moreover, CSRs are persistent to the `/tmp` folder. 
Details on errors returned by the Symantec VICE API can be found [here](https://support.venafi.com/hc/en-us/articles/215914347-Info-VeriSign-Symantec-MPKI-Error-Codes).

