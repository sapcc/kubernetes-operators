DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/example-operator
VERSION = v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := example

LDFLAGS := -X github.com/sapcc/kubernetes-operators/example/pkg/example.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

.PHONY: all clean

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build: bin/linux/$(BINARY)
	docker build -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*
