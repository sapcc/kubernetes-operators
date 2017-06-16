Sentry operator
====================
This k8s operators takes care of creating projects in a [Sentry](https://sentry.io) installation using a custom third party resource.
The operator exports the projects client key (DSN) as a kubernetes secret in the same namespace.

Usage
=====
Given the operator is correctly deployed in your cluster you can create/use a sentry project be creating a `SentryProject` TPR resource:

```
apiVersion: "sentry.sap.cc/v1"
kind: "SentryProject"
metadata:
  name: my-sentry-project 
  namespace: myns
spec:
  name: projectx #slug of the project you want to use (or create
  team: teamawesome #slug of the team where the project should be created (if it doesn't exist) 
```

The operator then takes care of ensuring that project exists in Sentry and creates/updates the `Secret` "sentry" in the same namespace and adds two keys:
```
kind: Secret
apiVersion: v1
metadata:
  name: sentry
  namespace: myns
data:
  projectx.DSN: aHR0cHM6Ly8wNzNiY2RmYTI5MTk0YjcwOTMyNDBkY2Y1MDBlNGQyMDo3NDY0MGYzYWNjMjY0NTE5OTdkMzM5YmMxNWY1MWFlNkBzZW50cnkuc3RhZ2luZy5jbG91ZC5zYXAvMTE1
  projectx.DSN.public: aHR0cHM6Ly8wNzNiY2RmYTI5MTk0YjcwOTMyNDBkY2Y1MDBlNGQyMEBzZW50cnkuc3RhZ2luZy5jbG91ZC5zYXAvMTE1
  [...]
```

You can reference these secrets in the usual way.


Notable CLI flags
=================

 * `--kubeconfig`: Path to kubeconfig file with authorization and master location information.
 * `--sentry-endpoint`: API endpoint for the sentry installation (default: https://sentry.io/api/0/)
 * `--sentry-token`: Authentication token for the sentry api **required**
 * `--sentry-organization`: The slug of the organization where teams and projects should be created by the operator **required** 

Notes
=====

To exclude external IPs from this service you can add the annotation `externalip.sap.cc/ignore: true` to the service spec.

