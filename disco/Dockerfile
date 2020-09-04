FROM golang:1.13.1-alpine3.10 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/disco
RUN apk add --no-cache make
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.10
MAINTAINER Arno Uhlig <arno.uhlig@@sap.com>
LABEL source_repository="https://github.com/sapcc/kubernetes-operators"

RUN apk add --no-cache ca-certificates curl tini
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/disco/bin/linux/disco /usr/local/bin/
RUN ["disco", "--version"]
ENTRYPOINT ["tini", "--"]
CMD ["disco"]
