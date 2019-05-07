FROM ubuntu:xenial
MAINTAINER Rudolf Vriend <rudolf.vriend@sap.com>

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf && \
    apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates wget curl && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Root_CA.crt http://cdp.pki.co.sap.com/cdp/SAP%20Global%20Root%20CA.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_02.crt http://cdp.pki.co.sap.com/cdp/SAP%20Global%20Sub%20CA%2002.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_04.crt http://cdp.pki.co.sap.com/cdp/SAP%20Global%20Sub%20CA%2004.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_05.crt http://cdp.pki.co.sap.com/cdp/SAP%20Global%20Sub%20CA%2005.crt && \
    wget -O /usr/local/share/ca-certificates/SAPNetCA_G2.crt http://cdp.pki.co.sap.com/cdp/SAPNetCA_G2.crt && \
    update-ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

RUN curl -sLo /usr/local/bin/kubernetes-entrypoint https://github.wdf.sap.corp/d062284/k8s-entrypoint-build/releases/download/f52d105/kubernetes-entrypoint && \
    chmod +x /usr/local/bin/kubernetes-entrypoint

WORKDIR /openstack-seeder
COPY python/* /openstack-seeder/
RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends build-essential pkg-config git openssl libssl-dev libyaml-dev libffi-dev python python-setuptools python-dev && \
    python setup.py install && \
    apt-get purge -y --auto-remove build-essential pkg-config git python-dev libssl-dev libffi-dev libyaml-dev && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

WORKDIR /
ADD bin/linux/openstack-seeder /usr/local/bin
