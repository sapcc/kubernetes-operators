# Kubernetes Openstack Operators

This repository holds operators that automate common tasks for managing
Openstack on Kubernetes.

We define an operator as piece of software that uses Kubernetes primitives to
model domain specific operational tasks. It extends Kubernetes using best
practices and controller concepts to remote control the system through the API
on behalf of a Kubernetes user. Using the third party resource mechanismm, this
allows us to detangle configuration changes and offloads the burden of
generating and reconfiguring the system into a dynamic runtime component.

See also: [CoreOS - Introducing Operators](https://coreos.com/blog/introducing-operators.html)


## Example 

As an example, a ThirdPartyResource `BuildingBlock` drives the creation of
a set of Nova-Agents through a `DeploymentSpec`. The operator will watch for
changes on `BuildingBlock` events and create/update the specs for the nova
agents. Additionally, it could remote control auxiliary systems, like sending a
status notification when a builing block goes into maintenance mode.

Now that building block configuration can be manages as Kubernetes spec, we
have a standarized way of changing the system's configuration - through
Kubernetes. This decoupling reduces the churn on the redeployment of the whole
system and makes changes easy and documentable. 

Additionally, "change" is now easy to compose even across system boundaries.
A new building block can be onboarded with an automated process, directly from
a build pipeline, triggered by a Git commit. Even auto-registration is
a thinkable scenario now. The building block could come with an agent that
talks directly to Kubernetes.


## Design Principles

Operators are build in Go. They use kubernetes/client-go to interface with the 
Kubernetes API. They follow the Kubernetes controller best practices and
programatically manage resources. 

Operators have one job and do that job well. They are easy to reason about. 


## Prior Art

kube-parrot
etcd-operator
prometheus-operator
kubernetes-certificate-manager
