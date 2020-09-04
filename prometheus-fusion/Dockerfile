FROM golang:1.9-alpine3.7 as builder
WORKDIR /go/src/github.com/sapcc/kubernetes-operators/prometheus-fusion
RUN apk add --no-cache make
COPY . .
ARG VERSION
RUN make all

FROM alpine:3.7
MAINTAINER Arno Uhlig <arno.uhlig@@sap.com>
LABEL source_repository="https://github.com/sapcc/kubernetes-operators"

RUN apk add --no-cache curl
RUN curl -Lo /bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 \
	&& chmod +x /bin/dumb-init \
	&& dumb-init -V
COPY --from=builder /go/src/github.com/sapcc/kubernetes-operators/prometheus-fusion/bin/linux/prometheus-fusion /usr/local/bin/
ENTRYPOINT ["dumb-init", "--"]
CMD ["prometheus-fusion"]
