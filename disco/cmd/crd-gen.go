package main

import (
	"fmt"
	"os"

	crdutils "github.com/ant31/crd-validation/pkg"
	"github.com/sapcc/kubernetes-operators/disco/pkg/k8sutils"
)

func main() {
	crd := k8sutils.NewDiscoCRD()
	if err := crdutils.MarshallCrd(crd, "yaml"); err != nil {
		fmt.Println("Error: ", err)
		os.Exit(1)
	}
	os.Exit(0)
}
