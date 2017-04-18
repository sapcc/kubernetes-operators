FROM alpine
MAINTAINER Fabian Ruff <fabian.ruff@sap.com> 

ADD bin/linux/externalip externalip
RUN /externalip --version

ENTRYPOINT ["/externalip"]
