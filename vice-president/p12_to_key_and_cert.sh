#!/bin/bash
if [[ "$#" -ne 1 ]]; then
  echo "usage: p12_to_key_and_cert <cert.p12>";
  exit 1;
fi
openssl pkcs12 -in $(pwd)/$1 -nocerts -nodes -out $(pwd)/$1.key
openssl pkcs12 -in $(pwd)/$1 -clcerts -nokeys -nodes -out $(pwd)/$1.pem
