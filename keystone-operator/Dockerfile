FROM python:2.7.13
MAINTAINER Rudolf Vriend <rudolf.vriend@sap.com>

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf && \
    apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https ca-certificates curl wget build-essential libpython2.7-dev libssl-dev openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN wget -O /usr/local/share/ca-certificates/SAP_Global_Root_CA.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Root%20CA.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_02.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Sub%20CA%2002.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_04.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Sub%20CA%2004.crt && \
    wget -O /usr/local/share/ca-certificates/SAP_Global_Sub_CA_05.crt http://aia.pki.co.sap.com/aia/SAP%20Global%20Sub%20CA%2005.crt && \
    wget -O /usr/local/share/ca-certificates/SAPNetCA_G2.crt http://aia.pki.co.sap.com/aia/SAPNetCA_G2.crt && \
    update-ca-certificates

RUN curl -sLo /usr/local/bin/kubernetes-entrypoint https://github.wdf.sap.corp/d062284/k8s-entrypoint-build/releases/download/f52d105/kubernetes-entrypoint && \
    chmod +x /usr/local/bin/kubernetes-entrypoint

WORKDIR /keystone-seeder
COPY python/* /keystone-seeder/
RUN python setup.py install

WORKDIR /
ADD bin/linux/keystone-operator keystone-operator
