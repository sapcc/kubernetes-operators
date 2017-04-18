External IP operator
====================
This k8s operators picks up `externalIPs` from `Service` resources and adds ore removes them to a local network interface.

We use this in conjunction with [kube-parrot](https://github.com/sapcc/kube-parrot) which announces `externalIPs` via BGP.

By adding those IPs to local interfaces they become pingable instead of Looping between kubernets nodes and routes until the TTL is reached.

Notable CLI flags
=================

 * `--kubeconfig`: Path to kubeconfig file with authorization and master location information.
 * `--interface`: Local interface where external IPs should be added. **(required)**
 * `--ignore-address`: ip addresses or CIDR ranges that should not be added or removed from the local interface. Can be specified multiple times.

Notes
=====

To exclude external IPs from this service you can add the annotation `externalip.sap.cc/ignore: true` to the service spec.