# Example Operator

This operator is a skeleton for other operators. It is intended to reflect best
practices for project setup, build process and kubernetes api interaction.

## Pod Debugger

The debugger shows how to use the informer framework to watch for changes on
pods. 

This is slightly simplified due to the SharedInformerFactory not being
available in `client-go`. Truely shared informers are only required for complex
operators that run multiple parallel control loops similar to the Kubernetes
ControllerManager.

## Critters

The second example shows how to implement and watch a `ThirdPartyResource`. The
setup is slightly more involved.

The default kubernetes `clientset` is a collection of higher-level clients.
These clients know about Pods, Demonsets, and so on. In order to be able to
talk to a `ThirdPartyResource` a new client needs to be created. New types
and custom group version must be configured for each resource.

Before a TPR can be used it needs to be registered, either via YAML upload or
through the API. Here we ensure it is created via code.

Afterwards, the Informer framework can be used to easily watch for changes in
a similar fasion.

The scenario can be tested by creating and deleting some critters:

```
kubectl create -f specs/
kubectl delete critter hamster
kubectl delete critter lizard
```

You will see:

```
2016/12/02 16:50:51 Critter ADDED: Michael's new hamster is orange
2016/12/02 16:50:51 Critter ADDED: Esther's new lizard is green
2016/12/02 16:50:54 Critter DELETED: Esther's green lizard just died... :(
2016/12/02 16:50:57 Critter DELETED: Michael's orange hamster just died... :(
```


