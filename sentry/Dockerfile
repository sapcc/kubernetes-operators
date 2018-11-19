FROM alpine:3.8
MAINTAINER Fabian Ruff <fabian.ruff@sap.com> 

RUN apk add --no-cache ca-certificates curl \
    && curl -fL http://aia.pki.co.sap.com/aia/SAP%20Global%20Root%20CA.crt | tr -d '\r' > /usr/local/share/ca-certificates/SAP_Global_Root_CA.crt \
    && update-ca-certificates \
    && curl https://github.wdf.sap.corp
ADD bin/linux/sentry-operator sentry-operator
RUN /sentry-operator --version

ENTRYPOINT ["/sentry-operator"]
CMD ["--logtostderr"]
