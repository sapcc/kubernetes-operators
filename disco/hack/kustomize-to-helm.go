package main

import (
	"bufio"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v2"
)

func main() {
	var outPath string
	flag.StringVar(&outPath, "out", "",
		"The path to the helm-chart directory")
	flag.Parse()

	if outPath == "" {
		fmt.Println("--out must be specified")
		os.Exit(1)
	}

	dec := yaml.NewDecoder(bufio.NewReader(os.Stdin))
	dec.SetStrict(true)
	for {
		data := map[string]interface{}{}
		if err := dec.Decode(&data); err != nil {
			if err.Error() == "EOF" {
				break
			}
			handleError(err)
		}

		metadata, ok := data["metadata"]
		if !ok {
			continue
		}
		metadataMap, ok := metadata.(map[interface{}]interface{})
		if !ok {
			continue
		}
		name, ok := metadataMap["name"]
		if !ok {
			continue
		}

		p, err := yaml.Marshal(data)
		handleError(err)

		dir := "templates"
		// Write CRDs to the /crds folder
		if data["kind"] == "CustomResourceDefinition" {
			dir = "crds"
		}

		err = os.MkdirAll(filepath.Join(outPath, dir), 0644)
		handleError(err)

		fileName := filepath.Join(outPath, dir, fmt.Sprintf("%s.yaml", name))
		fmt.Printf("writing file %s\n", fileName)
		err = ioutil.WriteFile(fileName, p, 0644)
		handleError(err)
	}
}

func handleError(err error) {
	if err != nil {
		fmt.Println("fatal error", err.Error())
		os.Exit(1)
	}
}
