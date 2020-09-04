FROM scratch
MAINTAINER Michael Schmidt <michael.schmidt02@@sap.com>
LABEL source_repository="https://github.com/sapcc/kubernetes-operators"

ADD bin/linux/helm-garbagecollector helm-garbagecollector

ENTRYPOINT ["/helm-garbagecollector"]
