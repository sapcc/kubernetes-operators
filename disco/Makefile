DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/disco
VERSION = v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := disco

LDFLAGS := -X github.com/sapcc/kubernetes-operators/disco/pkg/disco.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

GLIDE := $(shell command -v glide 2> /dev/null)

.PHONY: all clean vendor tests static-check

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/$(BINARY) ./cmd

build: bin/linux/$(BINARY)
	docker build -t $(IMAGE):$(VERSION) .

static-check:
	@if s="$$(gofmt -s -l *.go pkg 2>/dev/null)"                            && test -n "$$s"; then printf ' => %s\n%s\n' gofmt  "$$s"; false; fi
	@if s="$$(golint . && find pkg -type d -exec golint {} \; 2>/dev/null)" && test -n "$$s"; then printf ' => %s\n%s\n' golint "$$s"; false; fi

tests: all static-check
	DEBUG=1 && go test -v github.com/sapcc/kubernetes-operators/disco/pkg/disco

push: build
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*

vendor:
	dep ensure

.PHONY: crd-gen
crd-gen:
    chmod +x vendor/k8s.io/code-generator/generate-groups.sh && \
	vendor/k8s.io/code-generator/generate-groups.sh all \
	  github.com/sapcc/kubernetes-operators/disco/pkg/client \
	  github.com/sapcc/kubernetes-operators/disco/pkg/apis \
	  disco.stable.sap.cc:v1
