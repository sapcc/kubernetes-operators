FROM alpine:3.5
MAINTAINER Fabian Ruff <fabian.ruff@sap.com> 

ADD bin/linux/sentry-operator sentry-operator
RUN /sentry-operator --version

ENTRYPOINT ["/sentry-operator"]
CMD ["--logtostderr"]
