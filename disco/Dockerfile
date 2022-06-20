# syntax=docker/dockerfile:experimental
# Build the manager binary
FROM golang:1.18 as builder

RUN go install golang.org/x/tools/cmd/goimports@latest

WORKDIR /workspace
# Copy the Go Modules manifests
COPY go.mod go.mod
COPY go.sum go.sum
# cache deps before building and copying source so that we don't need to re-download as much
# and so that source changes don't invalidate our downloaded layer
RUN go mod download

# Miscellaneous
COPY Makefile Makefile
COPY hack/ hack/

# Copy the go source
COPY main.go main.go
COPY api/ api/
COPY controllers/ controllers/
COPY pkg/ pkg/

# Build
RUN --mount=type=cache,target=/go/pkg/mod \
	  --mount=type=cache,target=/root/.cache/go-build \
		CGO_ENABLED=0 GOOS=linux GOARCH=amd64 make build

# Use distroless as minimal base image to package the manager binary
# Refer to https://github.com/GoogleContainerTools/distroless for more details
FROM gcr.io/distroless/static:nonroot
LABEL source_repository="https://github.com/sapcc/kubernetes-operators/disco"
WORKDIR /
COPY --from=builder /workspace/bin/linux/disco .
USER 65532:65532

ENTRYPOINT ["/disco"]
