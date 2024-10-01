FROM alpine
LABEL source_repository="https://github.com/sapcc/kubernetes-operators"

RUN apk add --no-cache iptables

ADD bin/linux/externalip externalip
RUN /externalip --version

ENTRYPOINT ["/externalip"]
