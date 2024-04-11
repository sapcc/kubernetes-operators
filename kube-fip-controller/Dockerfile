FROM golang:alpine as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/kube-fip-controller
RUN apk add --no-cache make
COPY . .
ARG VERSION
RUN make all

FROM alpine
MAINTAINER Arno Uhlig <arno.uhlig@@sap.com>
LABEL source_repository="https://github.com/sapcc/kubernetes-operators"

RUN apk -U upgrade && apk add --no-cache ca-certificates curl tini
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/kube-fip-controller/bin/linux/controller /usr/local/bin/
RUN ["controller", "--version"]

ENTRYPOINT ["tini", "--"]
CMD ["controller"]
