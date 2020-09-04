FROM golang:1.12.9-alpine3.10 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/vice-president
RUN apk add --no-cache make dep git mercurial
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.10
LABEL maintainer="Michael Schmidt <michael.schmidt02@@sap.com>, Arno Uhlig <arno.uhlig@sap.com>"
LABEL source_repository="https://github.com/sapcc/kubernetes-operators"

RUN apk add --no-cache tini ca-certificates wget
RUN tini --version
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/vice-president/bin/linux/vice-president /usr/local/bin/
ENTRYPOINT ["tini", "--"]
CMD ["vice-president"]
