# Do not use - still under development

# Openstack Operator

Seed your openstack content with a kubernetes operator.

- introduces a new ThirdPartyResource **openstackseed**
    - **kubectl get openstackseeds** lists all deployed openstack seeds
    - kubectl apply/delete can be used to maintain openstack seed specs
- the k8s openstack-operator watches the lifecycle events of these specs
- openstack seed specs can depend on another (hierarchy) 
- on a lifecycle event (in this case only create/update), the operator resolves 
  the dependencies of the specs (merges them) and does the seeding of the 
  merged seed

## Supported entities

- regions
- roles
- services
    - endpoints
- flavors
- domains
    - configuration
    - domain-role-assignments
    - projects
        - project-role-assignments
    - groups
        - group-role-assignments
    - users
        - user-role-assignments
       
    
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

- spawn a python seeder that does the actual seeding


## Todo's

- testing
- documentation
- sentry instrumentation