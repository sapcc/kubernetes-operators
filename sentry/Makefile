VERSION=0.3.0
LDFLAGS=-X github.com/sapcc/kubernetes-operators/sentry/pkg/operator.VERSION=$(VERSION)
IMAGE   ?= sapcc/kube-sentry
GOOS    ?= darwin

GOFLAGS := -ldflags "$(LDFLAGS)"

CMDDIR   := cmd
PKGDIR   := pkg
PACKAGES := $(shell find $(CMDDIR) $(PKGDIR) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

.PHONY: all clean

all: bin/$(GOOS)/sentry-operator

bin/%/sentry-operator: $(GOFILES) go.mod Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -o bin/$*/sentry-operator ./cmd

build: bin/linux/sentry-operator
	docker build $(BUILD_ARGS) -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*
