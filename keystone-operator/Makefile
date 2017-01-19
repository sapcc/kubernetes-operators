DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= hub.global.cloud.sap/monsoon3/keystone-operator
VERSION ?= v$(DATE)
GOOS    ?= darwin
BINARY  := keystone-operator

LDFLAGS := -X github.com/sapcc/kubernetes-operators/keystone-operator/pkg/seeder.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

.PHONY: all clean build push linux darwin

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build: bin/linux/$(BINARY)
	docker build -t $(IMAGE):$(VERSION) .

push: build
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*

linux:  bin/linux/keystone-operator
darwin: bin/darwin/keystone-operator