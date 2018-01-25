FROM golang:1.9-alpine3.7 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/disco
RUN apk add --no-cache make
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.7
MAINTAINER Arno Uhlig <arno.uhlig@@sap.com>

RUN apk add --no-cache curl
RUN curl -Lo /bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 \
	&& chmod +x /bin/dumb-init \
	&& dumb-init -V
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/disco/bin/linux/disco /usr/local/bin/
ENTRYPOINT ["dumb-init", "--"]
CMD ["disco"]
