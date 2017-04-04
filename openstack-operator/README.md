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
  
Seeding currently only support creating or updating of entities (the operator upserts).  

## Supported entities

- regions
- roles
- services
    - endpoints
- flavors (untested)
- domains
    - configuration
    - domain-role-assignments
    - projects
        - project-role-assignments
    - groups
        - group-role-assignments
    - users
        - user-role-assignments
       
    
## Spec format
    
The seeding content can be provided in the usual kubernets spec yaml format.

The exact specfification of the seed format can be found in the pkg/seeder/openstackseed go doc.    
    
Example seed spec:
    
    apiVersion: "openstack.stable.sap.cc/v1"
    kind: "OpenstackSeed"
    metadata:
      name: keystone-seed
      labels:
        app: {{ template "fullname" . }}
        chart: "{{ .Chart.Name }}-{{ .Chart.Version }}"
        release: "{{ .Release.Name }}"
        heritage: "{{ .Release.Service }}"
    spec:
      roles:
      - admin
      - member
      - service
    
      regions:
      - id: eu
        description: 'Europe'
      - id: staging
        description: 'Staging'
        parent_region_id: eu
      - id: qa
        description: 'QA'
        parent_region_id: eu
      - id: local
        description: 'Local Development'
    
      services:
      - name: keystone
        type: identity
        description: Openstack Identity
        endpoints:
        - region: local
          interface: public
          url: {{ .Value.keystoneUrl }}:5000/v3
          enabled: true
        - region: local
          interface: admin
          url: {{ .Value.keystoneUrl }}:35357/v3
          enabled: true
        - region: local
          interface: internal
          url: http://keystone.{{.Release.Namespace}}.svc.kubernetes.{{.Values.region}}.{{.Values.tld}}:5000/v3'
          enabled: false
    
      domains:
      - name: Default
        id: default
        description: Openstack Internal Domain
        enabled: true
        users:
        - name: admin
          description: Openstack Cloud Administrator
          enabled: true
          password: secret123
          roles:
          - domain: Default
            role: admin
          - project: admin
            role: admin
          - project: service
            role: admin
    
        groups:
        - name: administrators
          description: Administrators
          roles:
          - domain: Default
            role: admin
          - project: admin
            role: admin
          - project: service
            role: admin
          users:
          - admin
        - name: members
          description: Members
          roles:
          - domain: Default
            role: member
        projects:
        - name: admin
          description: Administrator Project
        - name: service
          description: Services Project    
    
    
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
