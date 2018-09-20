FROM python:2 as pybuild

COPY python/setup.py /openstack-seeder/
RUN mkdir /wheels && pip wheel -w /wheels /openstack-seeder/ && rm /wheels/openstack_seeder*

FROM golang:1 as gobuild
ARG NS=github.com/sapcc/kubernetes-operators/openstack-seeder
RUN mkdir -p /go/src/$NS
WORKDIR /go/src/$NS
ADD vendor ./vendor
ADD cmd ./cmd
ADD pkg ./pkg
ARG VERSION
RUN go build\
    -v -i -o /openstack-seeder \
    -ldflags "-X github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/controller.VERSION=${VERSION}"\
    ./cmd

FROM python:2-slim
MAINTAINER Rudolf Vriend <rudolf.vriend@sap.com>

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf && \
    apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates wget curl && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Root_CA.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Root%20CA.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_02.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Sub%20CA%2002.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_04.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Sub%20CA%2004.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_05.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Sub%20CA%2005.crt && \
    wget -O /usr/local/share/ca-certificates/SAPNetCA_G2.crt http://aia.pki.co.sap.com/aia/SAPNetCA_G2.crt && \
    update-ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

RUN curl -Lo /bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 \
	&& chmod +x /bin/dumb-init \
	&& dumb-init -V

COPY --from=pybuild /wheels /wheels
WORKDIR /openstack-seeder
COPY python/* /openstack-seeder/
RUN pip install --no-cache-dir --no-compile --no-index --find-links /wheels -e /openstack-seeder && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

COPY --from=gobuild /openstack-seeder /usr/local/bin

WORKDIR /

ENTRYPOINT ["dumb-init", "--"]
CMD ["openstack-seeder"]