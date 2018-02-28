# Prometheus Fusion

[![Docker Repository](https://img.shields.io/docker/pulls/sapcc/coo.svg?maxAge=604800)](https://hub.docker.com/r/sapcc/prometheus-fusion/)

If you're on Kubernetes and using helm to manage resources you might have wondered why your application-specific Prometheus recording rules or alerts have to reside in the central Prometheus chart and not with the application?
This operator helps you untangling that.

# Features

- Automatic and periodically discovery of Configmaps containing Prometheus recording rules and alerts using Kubernetes API
- Collect rules and alerts and validates them
- Generates Configmap for Prometheus

# Usage

(0) Deploy using [helm chart](https://github.com/sapcc/helm-charts/tree/master/system/kube-system/charts/prometheus-fusion)  
(1) Store Prometheus recording rules and/or alerts in a Configmap.   
(2) Annotate that Configmap with `prometheus.io/rule`.  
(3) Annotate Prometheus' Configmap with `prometheus.io/configmap`.  
(4) Start the operator:
```
Usage of prometheus-fusion:
      --prom-cm-name string              Name of the prometheus configmap (optional)
      --prom-cm-namespace string         Namespace of the prometheus configmap (optional)
      --cm-annotation string             Only configmaps with this annotation will be considered (default "prometheus.io/rule")
      --kubeconfig string                Path to kubeconfig file with authorization and master location information (optional)
      --metric-port int                  Port on which Prometheus metrics are exposed (default 9091)
      --recheck-period int               RecheckPeriod[min] defines the base period after which configmaps are checked again (default 5)
      --resync-period int                ResyncPeriod[min] defines the base period after which the cache is resynced (default 2)
```
Note: The flags `--prom-cm-namesapce` and `--prom-cm-name` are optional, if you did (3) - in which case the operator attempts to discover Prometheus' Configmap.

# Limits

It's outside of the operators scope to signal Prometheus to reload its configuration after it was changed. However this is solved by [jimmidyson/configmap-reload](https://github.com/jimmidyson/configmap-reload).
