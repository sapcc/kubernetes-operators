VCenter Operator
=============

The VCenter Operator automatically configures and deploys cinder and nova-compute nodes corresponding to the discovered vcenters and clusters.
It follows the convention over configuration principle to keep the configuration to a minimum. It relies heavily on a other configmaps being deployed by `openstack-helm <https://github.com/sapcc/openstack-helm>`_  and should be best deployed with it.


Configuration
-------------------

Some basic configuration is however necessary. The VCenter Operator has to be deployed in a way that it allows it to deploy and modify resources within the configured target namespace.
The following values are required to be stored in a configmap named `vcenter-operator` in the same namespace as the running pod, and expects the following values:


namespace
    The namespace to deploy into

username
    The username to use to log on the vcenter

password
    A password used as a seed for the `master-password algorithm <http://masterpasswordapp.com/algorithm.html>` to generate long-form passwords specific for each vcenter discovered.

cinder_agent_image
    A docker image for a vcenter cinder volume

cinder_sentry_dsn
    Optionally, a Sentry DSN for the process

neutron_agent_image
    A docker image for the networking side of the compute node (currently only `Networking DVS Driver <https://github.com/sapcc/networking-dvs>`_)

nova_agent_image
    A docker image for the nova compute process.

cinder_sentry_dsn/neutron_sentry_dsn/nova_sentry_dsn
    Optionally, Sentry DSN, which will exported as environment variables


Conventions
-------------------

The vcenter operator relies on the following conventions:

- The operator relies on having dns as a kubernetes service with the labels `component=designate,type=backend`, and polls the DNS behind it.

- It polls the last search domain of the `resolv.conf`.

- Within that domain, the vcenter is expected to match `vc-[a-z]+-[0-9]+`.

-  The operator expects to be able to log on with username and the long form password derived by the given user and password for the fully-qualified domain name of the vcenter.

- Within the VCenter, the name of the VSphere datacenter will be used as the availability-zone name (in lower-case) for each entity child.

- Within a Datacenter, clusters prefixed with `production` will be used as compute nodes. The name of the compute-host will be the `nova-compute-<suffix>`, where `suffix` is whatever stands after `production` in the cluster-name.

- Within that cluster, the nova storage will be derived by looking for mounted storage prefixed by `eph`. The longest common prefix will be used as a search pattern for the storage of the compute node.

- The first Port-group within that cluster prefixed with `br-` will be used for the vm networking, and the suffix determines the physical name of the network.

- A cluster prefixed with `storage` will cause the creation of a cinder nodes with the name `cinder-volume-vmware-<suffix>`. This is only provisional and should be replaced by one per datacenter.
