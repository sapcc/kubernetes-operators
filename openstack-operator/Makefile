DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= hub.global.cloud.sap/monsoon/openstack-operator
VERSION ?= v$(DATE)
GOOS    ?= darwin
BINARY  := openstack-operator

LDFLAGS := -X github.com/sapcc/kubernetes-operators/openstack-operator/pkg/seeder.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

ifneq ($(http_proxy),)
BUILD_ARGS+= --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg no_proxy=$(no_proxy)
endif

.PHONY: all clean build push linux darwin

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build: bin/linux/$(BINARY)
	docker build $(BUILD_ARGS) -t $(IMAGE):$(VERSION) .

push: build
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*

linux:  bin/linux/openstack-operator
darwin: bin/darwin/openstack-operator