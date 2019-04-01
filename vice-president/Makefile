DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/vice-president
VERSION = v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := vice-president

LDFLAGS := -X github.com/sapcc/kubernetes-operators/vice-president/pkg/president.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

.PHONY: all clean vendor tests static-check

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): vendor $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build: tests bin/linux/$(BINARY)
	docker build -t $(IMAGE):$(VERSION) .

static-check:
	@if s="$$(gofmt -s -l *.go pkg 2>/dev/null)"                            && test -n "$$s"; then printf ' => %s\n%s\n' gofmt  "$$s"; false; fi
	@if s="$$(golint . && find pkg -type d -exec golint {} \; 2>/dev/null)" && test -n "$$s"; then printf ' => %s\n%s\n' golint "$$s"; false; fi

tests: all static-check
	go test -v github.com/sapcc/kubernetes-operators/vice-president/pkg/president

push: build
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*

vendor:
	if ! [ -d "vendor" ]; then dep ensure -vendor-only -v; fi

generate-dummy-cert:
	mkdir tmp
	openssl genrsa -out tmp/ca.key 2048
	openssl req -new -x509 -days 365 -key tmp/ca.key -subj "/C=CN/ST=GD/L=SZ/O=Acme, Inc./CN=MyRootCA" -out tmp/ca.crt
	openssl req -newkey rsa:2048 -nodes -keyout tmp/cert.key -subj "/C=CN/ST=GD/L=SZ/O=Acme, Inc./CN=www.example.com" -out tmp/cert.csr
	openssl x509 -req -extfile <(printf "subjectAltName=DNS:example.com,DNS:www.example.com,DNS:www.my-example.com") -days 10 -in tmp/cert.csr -CA tmp/ca.crt -CAkey tmp/ca.key -CAcreateserial -out tmp/cert.pem
