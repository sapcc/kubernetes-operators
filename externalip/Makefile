VERSION=0.2.0
LDFLAGS=-X github.com/sapcc/kubernetes-operators/externalip/pkg/operator.VERSION=$(VERSION)
IMAGE   ?= sapcc/kube-externalip
GOOS    ?= darwin

GOFLAGS := -ldflags "$(LDFLAGS)"

CMDDIR   := cmd
PKGDIR   := pkg
PACKAGES := $(shell find $(CMDDIR) $(PKGDIR) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

.PHONY: all clean

all: bin/$(GOOS)/externalip

bin/%/externalip: $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/externalip ./cmd

build: bin/linux/externalip
	docker build -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*
