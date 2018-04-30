# Designate IngresS Cname Operator (DISCO) 

[![Docker Repository](https://img.shields.io/docker/pulls/sapcc/disco.svg?maxAge=604800)](https://hub.docker.com/r/sapcc/disco/)


The DISCO operator automatically discovers Ingresses in the Kubernetes cluster and creates corresponding CNAMEs in OpenStack Desginate. 

## Features

  - Discovers required CNAMEs via Kubernetes API  
  - Automatically creates CNAMEs via OpenStack Designate API
  - Periodically verifies CNAMEs
  - Automatically deletes CNAMEs when the Ingress is deleted
  - Exposes Prometheus metrics 

## Requirements

  - go 1.9

## Usage

The [helm chart](https://github.com/sapcc/helm-charts/tree/master/system/kube-system/charts/disco/) can be used to bring the DISCO to your cluster.  
Note that the DISCO will only start for Ingresses that are annotated with
```
metadata:
  annotations:
    disco: "true"
```

**Fine-tuning:**  

The operator has to be configured with a default record.
However, this can also be set on the ingress using the following annotation:
```
disco/record: < record >
```

Per default type of all records will be `CNAME`.
This can be set to one of `A`, `SOA`, `NS`, `CNAME` using the following annotation:
```
disco/record-type: <record type>
```

Moreover, a description can be provided via the annotation:
```
disco/record-description: < description >
``` 

## Configuration

To be able to authenticate with OpenStack the operator requires the following parameters in the configuration:
```
auth_url:             <OS_AUTH_URL>
region_name:          <OS_REGION_NAME>
username:             <OS_USERNAME>
user_domain_name:     <OS_USER_DOMAIN_NAME>
password:             <OS_PASSWORD>
project_name:         <OS_PROJECT_NAME>
project_domain_name:  <OS_PROJECT_DOMAIN_NAME>
```

Moreover the following parameters need to be set:
```
Usage of disco:
  --config string                    Path to operator config file (default "/etc/disco/disco.conf")
  --record string                    Default record data used for the CNAME
  --zone-name string                 Name of the zone in which the recordset will be created
```

Given the following Ingress
```
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    disco: "true"
  
... 
 
spec:
  rules:
  - host: myhost.zone.tld
    ...
```
the operator would create the following CNAME in the configured zone in OpenStack Designate
```
+-----------------------+-------+----------------+
| name                  | type  | records        |
+------------------------------------------------+
| myhost.zone.tld.      | CNAME | <record>       |
+-----------------------+-------+----------------+
```

All parameters and their defaults:
```
Usage of disco:
    --alsologtostderr                  log to standard error as well as files
    --config string                    Path to operator config file (default "/etc/disco/disco.conf")
    --ingress-annotation string        Handle ingress with this annotation (default "disco")
    --kubeconfig string                Path to kubeconfig file with authorization and master location information
    --log_backtrace_at traceLocation   when logging hits line file:N, emit a stack trace (default :0)
    --log_dir string                   If non-empty, write log files in this directory
    --logtostderr                      log to standard error instead of files
    --metric-port int                  Metrics are exposed on this port (default 9091)
    --recheck-period int               RecheckPeriod[min] defines the base period after which configmaps are checked again (default 5)
    --record string                    Default record data used for the CNAME
    --recordset-ttl int                The Recordset TTL in seconds (default 1800)
    --resync-period int                ResyncPeriod[min] defines the base period after which the cache is resynced (default 2)
    --stderrthreshold severity         logs at or above this threshold go to stderr (default 2)
    --threadiness int                  The operator threadiness (default 1)
-v, --v Level                          log level for V logs
    --vmodule moduleSpec               comma-separated list of pattern=N settings for file-filtered logging
    --zone-name string                 Name of the zone in which the recordset will be created
```

## Limitations

If an Ingress defines multiple hosts, as shown below, deleting one rule will currently not trigger the deletion of the record in Designate.
```
spec:
  rules:
  - host: party.subdomain.tld
    http:
      paths:
      - backend:
          serviceName: party-service
          servicePort: 80
        path: /
  - host: disco.subdomain.tld
    http:
      paths:
      - backend:
          serviceName: disco-service
          servicePort: 80
        path: /
```