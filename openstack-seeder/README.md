# Openstack Seeder

Seed your openstack content with a kubernetes operator.

- introduces a new kubernetes CustomResourceDefinition **openstackseed**
    - **kubectl get openstackseeds** lists all deployed openstack seeds
    - kubectl apply/delete can be used to maintain openstack seed specs
- the k8s openstack-seeder watches the lifecycle events of these specs
- openstack seed specs can depend on another (hierarchy) 
- on a lifecycle event of a seed spec (only create/update), the operator resolves 
  the dependencies of the specs (merges them) and invokes the seeding of the 
  merged seed spec
  
Seeding currently only supports creating or updating of entities (upserts).  

## Supported entities

- regions
- roles
- role_inferences
- services
    - endpoints
- flavors
    - extra-specs
- domains
    - configuration
    - domain-role-assignments
    - projects
        - project-role-assignments
        - project-endpoints
        - network quotas
        - address scopes
            - subnet pools
        - subnet pools
        - networks
            - tags
            - subnets
        - routers
            - interfaces
        - swift 
            - account
            - containers
        - dns_quota
        - dns_zones
            - recordsets
        - dns_tsigkeys
        - ec2_creds
        - flavors
    - groups
        - group-role-assignments
    - users
        - user-role-assignments
    - roles
       
    
## Spec format
    
The seeding content can be provided in the usual kubernets spec yaml format.

The exact specfification of the seed format can be found in the pkg/seeder/apis/v1/types go doc.    
    
Example seed spec of a keystone seed to be deployed via helm:
    
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
      - name: admin
        description: 'Keystone Administration'
      - name: member
        description: 'Keystone Member'
      - name: reader
        description: 'Keystone Read-Only'
      - name: service
        description: 'Keystone Service'
    
      role_inferences:
      - prior_role: admin
        implied_role: member
        
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
          role_assignments:
          - domain: Default
            role: admin
          - project: admin
            role: admin
          - project: service
            role: admin
    
        groups:
        - name: administrators
          description: Administrators
          role_assignments:
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
          role_assignments:
          - domain: Default
            role: member
        projects:
        - name: admin
          description: Administrator Project
        - name: service
          description: Services Project    
    
    
## why did you not use gophercloud as a go openstack client?

When we started the implementation of the operator, the gophercloud api coverage was far from complete.
Hence we decided to spawn a python seeder that does the actual seeding via the python opensatck api clients.
