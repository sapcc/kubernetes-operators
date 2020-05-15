package hack

//this file is only here so that `glide list` picks
//up our dependencies not used in code.
//Otherwise glide-vc deletes it

import (
	_ "k8s.io/client-go/kubernetes/fake"
	_ "k8s.io/code-generator/cmd/client-gen"
	_ "k8s.io/code-generator/cmd/deepcopy-gen"
	_ "k8s.io/code-generator/cmd/informer-gen"
	_ "k8s.io/code-generator/cmd/lister-gen"
	_ "k8s.io/code-generator/cmd/openapi-gen"
)
