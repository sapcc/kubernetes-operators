OUTPUT         := _output
OUTPUT_BASE    := $(GOPATH)/src
INPUT_BASE     := github.com/sapcc/kubernetes-operators/openstack-seeder
API_BASE       := $(INPUT_BASE)/pkg/apis
GENERATED_BASE := $(INPUT_BASE)/pkg/client
BIN            := $(OUTPUT)/bin

.PHONY: client-gen informer-gen lister-gen deepcopy-gen openapi-gen

client-gen: $(BIN)/client-gen
	@rm -rf ./pkg/client/clientset
	@mkdir -p ./pkg/client/clientset
	$(BIN)/client-gen \
	  --go-header-file hack/custom-boilerplate.go.txt \
	  --output-base $(OUTPUT_BASE) \
	  --input-base $(API_BASE) \
	  --clientset-path $(GENERATED_BASE)/clientset \
	  --input seeder/v1 \
	  --clientset-name versioned

informer-gen: $(BIN)/informer-gen
	@rm -rf ./pkg/client/informers
	@mkdir -p ./pkg/client/informers
	$(BIN)/informer-gen \
	  --logtostderr \
	  --go-header-file hack/custom-boilerplate.go.txt \
	  --output-base                 $(OUTPUT_BASE) \
	  --input-dirs                  $(API_BASE)/seeder/v1  \
	  --output-package              $(GENERATED_BASE)/informers \
	  --listers-package             $(GENERATED_BASE)/listers   \
	  --internal-clientset-package  $(GENERATED_BASE)/clientset/versioned \
	  --versioned-clientset-package $(GENERATED_BASE)/clientset/versioned

lister-gen: $(BIN)/lister-gen
	@rm -rf ./pkg/client/listers
	@mkdir -p ./pkg/client/listers
	$(BIN)/lister-gen \
	  --logtostderr \
	  --go-header-file hack/custom-boilerplate.go.txt \
	  --output-base    $(OUTPUT_BASE) \
	  --input-dirs     $(API_BASE)/seeder/v1 \
	  --output-package $(GENERATED_BASE)/listers

deepcopy-gen: $(BIN)/deepcopy-gen
	@rm -rf $(API_BASE)/seeder/v1/zz_generated.deepcopy
	${BIN}/deepcopy-gen \
	  --input-dirs $(API_BASE)/seeder/v1 \
	  -O zz_generated.deepcopy \
	  --bounding-dirs $(INPUT_BASE) \
	  --output-base $(OUTPUT_BASE) \
	  --go-header-file hack/custom-boilerplate.go.txt

openapi-gen: $(BIN)/openapi-gen
	@rm -rf $(API_BASE)/seeder/v1/openapi_generated
	$(BIN)/openapi-gen  \
	  --logtostderr \
	  -i $(API_BASE)/seeder/v1 \
	  -p $(API_BASE)/seeder/v1 \
	  --go-header-file hack/custom-boilerplate.go.txt 

$(OUTPUT)/bin/%:
	@mkdir -p _output/bin
	go build -o $@ ./vendor/k8s.io/code-generator/cmd/$*
