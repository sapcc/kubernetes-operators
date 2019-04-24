DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= hub.global.cloud.sap/monsoon/openstack-seeder
#VERSION ?= v$(DATE)
VERSION ?= v1.10.$(shell git rev-parse --verify HEAD)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := openstack-seeder

LDFLAGS := -X github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/controller.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

ifeq ($(GOBIN),)
GOBIN :=${GOPATH}/bin
endif

REPO := github.com/sapcc/kubernetes-operators/openstack-seeder

BUILD_ARGS := --build-arg VERSION=$(VERSION)
ifneq ($(http_proxy),)
BUILD_ARGS+= --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg no_proxy=$(no_proxy)
endif

OPENAPI_GEN := $(shell command -v openapi-gen 2> /dev/null)

HAS_GLIDE := $(shell command -v glide;)
HAS_GLIDE_VC := $(shell command -v glide-vc;)

.PHONY: all clean build push linux darwin vendor openapi-gen

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): $(GOFILES) Makefile code-gen
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build:
	docker build $(BUILD_ARGS) -t $(IMAGE):$(VERSION) .

tag:
	docker tag $(IMAGE):$(VERSION) $(IMAGE):latest

pull:
	docker pull $(IMAGE):latest

push:
	docker push $(IMAGE):$(VERSION)
	docker push $(IMAGE):latest

clean:
	rm -rf bin/*
	rm -rf _output/*
	rm -rf vendor/*

include code-generate.mk
code-gen: client-gen informer-gen lister-gen deepcopy-gen generate-openapi

v1/openapi_generated.go: $(GOBIN)/openapi-gen
	openapi-gen  -i $(REPO)/pkg/apis/seeder/v1 -p $(REPO)/pkg/apis/seeder/v1 --go-header-file="$(GOPATH)/src/github.com/ant31/crd-validation/.header" --logtostderr

generate-openapi: v1/openapi_generated.go

vendor:
ifndef HAS_GLIDE_VC
	$(error glide-vc (vendor cleaner) not found. Run `make bootstrap to fix.`)
endif
	glide install -v
	glide-vc --only-code --no-tests

bootstrap:
ifndef HAS_GLIDE
	brew install glide
endif
ifndef HAS_GLIDE_VC
	go get -u github.com/sgotti/glide-vc
endif

$(GOBIN)/openapi-gen:
	go get -u -d k8s.io/code-generator/cmd/openapi-gen@kubernetes-1.10.13
	cd ${GOPATH}/src/k8s.io/code-generator/cmd/openapi-gen && git checkout release-1.10 && go install

linux:  bin/linux/openstack-seeder
darwin: bin/darwin/openstack-seeder