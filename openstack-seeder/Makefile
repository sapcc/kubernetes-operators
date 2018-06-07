DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= hub.global.cloud.sap/monsoon/openstack-seeder
VERSION ?= v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := openstack-seeder

LDFLAGS := -X github.com/sapcc/kubernetes-operators/openstack-seeder/pkg/seeder/controller.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

ifneq ($(http_proxy),)
BUILD_ARGS+= --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg no_proxy=$(no_proxy)
endif

HAS_GLIDE := $(shell command -v glide;)
HAS_GLIDE_VC := $(shell command -v glide-vc;)

.PHONY: all clean build push linux darwin vendor

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build: bin/linux/$(BINARY)
	docker build $(BUILD_ARGS) -t $(IMAGE):$(VERSION) .

tag:
	docker tag $(IMAGE):$(VERSION)         $(IMAGE):latest

pull:
	docker pull $(IMAGE):latest

push:
	docker push $(IMAGE):$(VERSION)
	docker push $(IMAGE):latest

clean:
	rm -rf bin/*

include code-generate.mk
code-gen: client-gen informer-gen lister-gen deepcopy-gen

vendor:
ifndef HAS_GLIDE_VC
	$(error glide-vc (vendor cleaner) not found. Run `make bootstrap to fix.`)
endif
	glide install -v
	#glide-vc --only-code --no-tests

bootstrap:
ifndef HAS_GLIDE
	brew install glide
endif
ifndef HAS_GLIDE_VC
	go get -u github.com/sgotti/glide-vc
endif

linux:  bin/linux/openstack-seeder
darwin: bin/darwin/openstack-seeder