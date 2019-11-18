FROM golang:1.13.4-alpine3.10 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/kube-fip-controller
RUN apk add --no-cache make
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.10
MAINTAINER Arno Uhlig <arno.uhlig@@sap.com>

RUN apk add --no-cache ca-certificates curl tini
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/kube-fip-controller/bin/linux/controller /usr/local/bin/
ENTRYPOINT ["tini", "--"]
CMD ["controller"]
