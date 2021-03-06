DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/prometheus-fusion
VERSION = v$(DATE)
GOOS    ?= $(shell go env | grep GOOS | cut -d'"' -f2)
BINARY  := prometheus-fusion

LDFLAGS := -X github.com/sapcc/kubernetes-operators/prometheus-fusion/pkg/fusion.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

SRCDIRS  := cmd pkg
PACKAGES := $(shell find $(SRCDIRS) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

GLIDE := $(shell command -v glide;)

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
	DEBUG=1 && go test -v github.com/sapcc/kubernetes-operators/prometheus-fusion/pkg/...

push: build
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*

vendor:
	ifndef GLIDE
		echo "Cannot vendor. Glide is not installed. Please do so now."
	else
		glide install --stip-vendor --strip-vcs
		glide-vc --only-code --no-tests
	endif
