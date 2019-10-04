DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/disco
VERSION = v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := disco

LDFLAGS := -X github.com/sapcc/kubernetes-operators/disco/pkg/disco.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GO_PKG	 := github.com/sapcc/kubernetes-operators/disco
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

OPENAPI_GEN_BINARY:=$(GOPATH)/bin/openapi-gen

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
	go mod tidy && go mod vendor

.PHONY: crd-gen
crd-gen: openapi-gen
	./hack/codegen.sh && $(GOBIN)/crd-gen > crd/record.disco.stable.sap.cc.crd.yaml

openapi-gen: $(CRDGEN_BINARY)
	$(OPENAPI_GEN_BINARY) \
	--go-header-file hack/boilerplate.go.txt \
	-i $(GO_PKG)/pkg/apis/disco.stable.sap.cc/v1 \
	-p $(GO_PKG)/pkg/apis/disco.stable.sap.cc/v1

$(CRDGEN_BINARY): cmd/crd-gen.go
	@go install -mod=vendor $(GO_PKG)/cmd/crd-gen.go
