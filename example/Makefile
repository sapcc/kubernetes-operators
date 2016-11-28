DATE    = $(shell date +%Y%m%d%H%M)
IMAGE   ?= sapcc/example-operator
VERSION = v$(DATE)
GOOS    ?= darwin

LDFLAGS := -X github.com/sapcc/kubernetes-operators/example/pkg/example.VERSION=$(VERSION)
GOFLAGS := -ldflags "$(LDFLAGS)"

CMDDIR   := cmd
PKGDIR   := pkg
PACKAGES := $(shell find $(CMDDIR) $(PKGDIR) -type d)
GOFILES  := $(addsuffix /*.go,$(PACKAGES))
GOFILES  := $(wildcard $(GOFILES))

.PHONY: all clean

all: bin/$(GOOS)/example

bin/%/example: $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -v -i -o bin/$*/example ./cmd

build: bin/linux/example
	docker build -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)

clean:
	rm -rf bin/*
