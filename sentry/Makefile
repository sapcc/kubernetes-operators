VERSION=0.1.0
LDFLAGS=-X github.com/sapcc/kubernetes-operators/sentry-operator/pkg/operator.VERSION=$(VERSION)
IMAGE   ?= sapcc/kube-sentry
GOOS    ?= darwin

GOFLAGS := -ldflags "$(LDFLAGS)"

CMDDIR   := cmd
PKGDIR   := pkg
PACKAGES := $(shell find $(CMDDIR) $(PKGDIR) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

ifneq ($(http_proxy),)
BUILD_ARGS+= --build-arg http_proxy=$(http_proxy) --build-arg https_proxy=$(https_proxy) --build-arg no_proxy=$(no_proxy)
endif

.PHONY: all clean

all: bin/$(GOOS)/sentry-operator

bin/%/sentry-operator: $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/sentry-operator ./cmd

build: bin/linux/sentry-operator
	docker build $(BUILD_ARGS) -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*
