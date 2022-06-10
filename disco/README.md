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

- go 1.18

## Installation

The [helm chart](https://github.com/sapcc/helm-charts/tree/master/system/kube-system/charts/disco/) can be used to bring the DISCO to your cluster.  
Note that the DISCO will only start for Ingresses that are annotated with
```
metadata:
  annotations:
    disco: "true"
```

## Configuration

The DISCO is configured via environment variables:
```
# Openstack configurations.
OS_AUTH_URL:
OS_REGION_NAME:
OS_USERNAME:
OS_PASSWORD:
OS_USER_DOMAIN_NAME:
OS_PROJECT_NAME:
OS_PROJECT_DOMAIN_NAME:

# Operator specifics.
DEFAULT_DNS_ZONE_NAME:
DEFAULT_DNS_RECORD:
```

## Usage

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

Given the following service:

```
apiVersion: v1
kind: Service
metadata
  annotations:
    disco: "true"
    disco/record: myhost.zone.tld.
spec:
  externalIPs:
  - 1.2.3.4
  loadBalancerIP: 1.2.3.4
  ...
status:
  loadBalancer:
    ingress:
    - ip: 1.2.3.4
```

the operator would create the following A record in the configured zone in OpenStack Designate
```
+-----------------------+-------+----------------+
| name                  | type  | records        |
+------------------------------------------------+
| myhost.zone.tld.      | A     | 1.2.3.4        |
+-----------------------+-------+----------------+
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

Creation of records in a different zone is supported via the annotation:
```
disco/zone-name: <name of the zone>
```

All parameters and their defaults:
```
Usage of disco:
      --config string               Path to operator config file (default "/etc/disco/disco.conf")
      --debug                       Enable debug logging
      --ingress-annotation string   Handle ingress with this annotation (default "disco")
      --service-annotation string   Handle service with this annotation (default "disco")
      --kubeconfig string           Path to kubeconfig file with authorization and master location information
      --metric-port int             Metrics are exposed on this port (default 9091)
      --recheck-period int          RecheckPeriod[min] defines the base period after which configmaps are checked again (default 5)
      --record string               Default record data used for the CNAME
      --recordset-ttl int           The Recordset TTL in seconds (default 1800)
      --resync-period int           ResyncPeriod[min] defines the base period after which the cache is resynced (default 2)
      --threadiness int             The operator threadiness (default 1)
      --zone-name string            Name of the openstack zone in which the recordset will be created
```

**Note**:
The DISCO operator uses [finalizers](https://kubernetes.io/docs/tasks/access-kubernetes-api/custom-resources/custom-resource-definitions/#finalizers)
to ensure the deletion of Designate CNAMEs when the deletion of the corresponding ingress is triggered.
Removing the finalizer manually will cause a left-over CNAME in Designate.

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

## Getting Started

You’ll need a Kubernetes cluster to run against. You can use [KIND](https://sigs.k8s.io/kind) to get a local cluster for testing, or run against a remote cluster.
**Note:** Your controller will automatically use the current context in your kubeconfig file (i.e. whatever cluster `kubectl cluster-info` shows).

### Running on the cluster
1. Install Instances of Custom Resources:

```sh
kubectl apply -f config/samples/
```

2. Build and push your image to the location specified by `IMG`:
	
```sh
make docker-build docker-push IMG=<some-registry>/disco:tag
```
	
3. Deploy the controller to the cluster with the image specified by `IMG`:

```sh
make deploy IMG=<some-registry>/disco:tag
```

### Uninstall CRDs
To delete the CRDs from the cluster:

```sh
make uninstall
```

### Undeploy controller
UnDeploy the controller to the cluster:

```sh
make undeploy
```

## Contributing
// TODO(user): Add detailed information on how you would like others to contribute to this project

### How it works
This project aims to follow the Kubernetes [Operator pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)

It uses [Controllers](https://kubernetes.io/docs/concepts/architecture/controller/) 
which provides a reconcile function responsible for synchronizing resources untile the desired state is reached on the cluster 

### Test It Out
1. Install the CRDs into the cluster:

```sh
make install
```

2. Run your controller (this will run in the foreground, so switch to a new terminal if you want to leave it running):

```sh
make run
```

**NOTE:** You can also run this in one step by running: `make install run`

## License

Copyright 2022 SAP SE.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

