FROM golang:1.11.0-alpine3.8 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/vice-president
RUN apk add --no-cache make dep git mercurial
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.8
LABEL maintainer="Michael Schmidt <michael.schmidt02@@sap.com>, Arno Uhlig <arno.uhlig@sap.com>"

RUN apk add --no-cache tini
RUN tini --version
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/vice-president/bin/linux/vice-president /usr/local/bin/
ENTRYPOINT ["tini", "--"]
CMD ["vice-president"]
