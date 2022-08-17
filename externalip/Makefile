VERSION=0.5.0
LDFLAGS=-X github.com/sapcc/kubernetes-operators/externalip/pkg/operator.VERSION=$(VERSION)
IMAGE   ?= keppel.eu-de-1.cloud.sap/ccloud/kube-externalip
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

all: bin/$(GOOS)/externalip

bin/%/externalip: $(GOFILES) Makefile
	GOOS=$* GOARCH=amd64 go build $(GOFLAGS) -mod vendor -v -i -o bin/$*/externalip ./cmd

build: bin/linux/externalip
	docker build $(BUILD_ARGS) -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)

docker-push-mac: bin/linux/externalip
	docker buildx build  --platform linux/amd64 . -t ${IMAGE}:${VERSION} --push

clean:
	rm -rf bin/*
