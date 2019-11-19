kube-fip-controller
-------------------

Controller that helps to run Kubernetes on OpenStack.  
It's capable of allocating and associating a Openstack Neutron Floating IP (FIP) with an existing Openstack server.

## Installation

The [Helm chart](https://github.com/sapcc/helm-charts/tree/master/system/kube-fip-controller) can be used to bring the controller to your cluster.

## Configuration

To be able to authenticate with OpenStack the controller requires the following parameters in the configuration:

```yaml
auth_url:             <OS_AUTH_URL>
region_name:          <OS_REGION_NAME>
username:             <OS_USERNAME>
user_domain_name:     <OS_USER_DOMAIN_NAME>
password:             <OS_PASSWORD>
project_name:         <OS_PROJECT_NAME>
project_domain_name:  <OS_PROJECT_DOMAIN_NAME>
```

The password can also be provided via the environment variable `OS_PASSWORD`.

Moreover, the controller needs a default OpenStack Neutron network and subnet for creating FIPs.
The names of these are passed via the flags:
```
--default-floating-network=$networkName
--default-floating-subnet=$subnetName
```


## Usage

The controller is activated via node annotations:
```
metadata:
  annotations:
    kube-fip-controller.ccloud.sap.com/enabled: "true"
```

Once the controller successfully created and associated the FIP with the server it will adds the `kube-fip-controller.ccloud.sap.com/externalIP: "$floatingIP"` to the node.
This annotation can also be used beforehand to specify the FIP.

Optionally, the annotations `kube-fip-controller.ccloud.sap.com/floating-network-name: "$networkName"`, `kube-fip-controller.ccloud.sap.com/floating-subnet-name: "$subnetName"`
can be used to specify the floating network and subnet used for the FIP.

