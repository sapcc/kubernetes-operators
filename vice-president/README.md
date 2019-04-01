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

  - Discovers required certificates via Kubernetes API  
  - Automatically requests Certificates via Symantec API
  - Periodically verifies Certificates 
  - Automatically renews certificates that would expire within one month
  - Exposes Prometheus metrics 

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
      --vice-config            string  Path to VICE config file with certificate parameters.
      --vice-cert              string  A PEM encoded certificate file.
      --vice-key               string  A PEM encoded private key file.
      
      optional:
      --kubeconfig             string  Path to kubeconfig file with authorization and master location information. Optional if vice president is deployed in a cluster.
      --ingress-annotation 	   string  Only an ingress with this annotation will be considered. (default: { "vice-president": true } )
      --metric-listen-address  string  Port on which Prometheus metrics are exposed. (default ":9091")
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

Check the log for further info. 
Details on errors returned by the Symantec VICE API can be found [here](https://support.venafi.com/hc/en-us/articles/215914347-Info-VeriSign-Symantec-MPKI-Error-Codes).
