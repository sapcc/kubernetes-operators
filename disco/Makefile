DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/disco
VERSION = v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := disco

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GO_PKG	 := github.com/sapcc/kubernetes-operators/disco
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

OPENAPI_GEN_BINARY:=$(GOPATH)/bin/openapi-gen

.PHONY: all clean vendor tests static-check

all: bin/$(GOOS)/$(BINARY)

bin/%/$(BINARY): BUILD_DATE  = $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
bin/%/$(BINARY): GIT_REVISION  = $(shell git rev-parse --short HEAD)
bin/%/$(BINARY): GIT_BRANCH = $(shell git rev-parse --abbrev-ref HEAD)
bin/%/$(BINARY): $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build\
		-ldflags "-s -w -X github.com/sapcc/kubernetes-operators/disco/pkg/version.Revision=$(GIT_REVISION) -X github.com/sapcc/kubernetes-operators/disco/pkg/version.Branch=$(GIT_BRANCH) -X github.com/sapcc/kubernetes-operators/disco/pkg/version.BuildDate=$(BUILD_DATE) -X github.com/sapcc/kubernetes-operators/disco/pkg/version.Version=$(VERSION)"\
		-v -o bin/$*/$(BINARY) ./cmd/$(BINARY)

docker-build: bin/linux/$(BINARY)
	docker build -t $(IMAGE):$(VERSION) .

static-check:
	@if s="$$(gofmt -s -l *.go pkg 2>/dev/null)"                            && test -n "$$s"; then printf ' => %s\n%s\n' gofmt  "$$s"; false; fi
	@if s="$$(golint . && find pkg -type d -exec golint {} \; 2>/dev/null)" && test -n "$$s"; then printf ' => %s\n%s\n' golint "$$s"; false; fi

tests: all static-check
	DEBUG=1 && go test -v github.com/sapcc/kubernetes-operators/disco/pkg/disco

docker-push: docker-build
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*

vendor:
	go mod tidy && go mod vendor

.PHONY: crd-gen
crd-gen: openapi-gen
	./hack/codegen.sh && go run -mod=vendor cmd/crd-gen/main.go > crd/record.disco.stable.sap.cc.crd.yaml

openapi-gen:
	$(OPENAPI_GEN_BINARY) \
	--go-header-file hack/boilerplate.go.txt \
	-i $(GO_PKG)/pkg/apis/disco/v1 \
	-p $(GO_PKG)/pkg/apis/disco/v1

