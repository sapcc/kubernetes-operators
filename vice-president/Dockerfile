FROM golang:1.9.3-alpine3.7 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/vice-president
RUN apk add --no-cache make
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.7
MAINTAINER Michael Schmidt <michael.schmidt02@@sap.com>

RUN apk add --no-cache curl
RUN curl -Lo /bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 \
	&& chmod +x /bin/dumb-init \
	&& dumb-init -V
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/vice-president/bin/linux/vice-president /usr/local/bin/
ENTRYPOINT ["dumb-init", "--"]
CMD ["vice-president"]
