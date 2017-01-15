# Helm Garbage Collector

This operator takes care of deleting superseded Helm releases. Without this
garbage collection all Helm operations gradually become slower and slower. This
is especially pronounced when installing large charts, like Openstack.

## Operations

Helm stores releases as ConfigMap in the kube-system namespace. They can be
identified by the label `OWNER=TILLER`. The status of a release is also stored
in a label `STATUS`, its version in a label `VERSION`.

The most recent release will have the status `DEPLOYED`. Previous releases that
are now superseded will be in status `SUPERSEDED`

This operator will watch all ConfigMaps that belong to Tiller. In
a configurable interval (`--gc-interval`, default: 300) it will delete all
superseded versions for each release. It will retain a configurable amount
(`--revision-history-limit`, default: 5) of versions.

## Manual Debug

```
kubectl get configmaps -l OWNER=TILLER -n kube-system
kubectl get configmaps -l OWNER=TILLER,STATUS=SUPERSEDED -n kube-system
```


