# Do not use - still under development

# Keystone Operator

Seed your keystone content via a kubernetes operator.

- introduces a new ThirdPartyResource **keystoneseed**
    - **kubectl get keystoneseeds** lists all deployed keystone seeds
    - kubectl apply/delete can be used to maintain keystone seed specs
- the k8s keystone-operator watches the lifecycle events of these specs
- keystone seed specs can depend on another (hierarchy) 
- on a lifecycle event (in this case only create/update), the operator resolves 
  the dependencies of the specs (merges them) and does the keystone seeding of the 
  merged keystone seed

## why not use gophercloud as openstack client?

### status
- widest openstack component api coverage of all go clients
- slow PR adoption, seems to be somewhat stalled

#### covered

- V2 users, tenants, role assignments
- authentication, token validation
- services
- endpoints
- project (list only)
- role assignments (list only)

#### open PR

- project CRUD

#### missing

- domains
- domain configuration
- users
- groups
- regions
- roles
- role assignment CRUD
- project endpoints

## workaround for missing gophercloud features

- spawn a python keystone seeder that does the actual seeding


## Todo's

- testing
- documentation