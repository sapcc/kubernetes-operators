package main

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
	"syscall"
	"time"

	"github.com/golang/glog"
	"github.com/sapcc/go-vice"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/president"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/regions"
	"github.com/spf13/pflag"
)

var options president.Options

const SYMANTEC_INTERMEDIATE = `
-----BEGIN CERTIFICATE-----
MIIFODCCBCCgAwIBAgIQUT+5dDhwtzRAQY0wkwaZ/zANBgkqhkiG9w0BAQsFADCB
yjELMAkGA1UEBhMCVVMxFzAVBgNVBAoTDlZlcmlTaWduLCBJbmMuMR8wHQYDVQQL
ExZWZXJpU2lnbiBUcnVzdCBOZXR3b3JrMTowOAYDVQQLEzEoYykgMjAwNiBWZXJp
U2lnbiwgSW5jLiAtIEZvciBhdXRob3JpemVkIHVzZSBvbmx5MUUwQwYDVQQDEzxW
ZXJpU2lnbiBDbGFzcyAzIFB1YmxpYyBQcmltYXJ5IENlcnRpZmljYXRpb24gQXV0
aG9yaXR5IC0gRzUwHhcNMTMxMDMxMDAwMDAwWhcNMjMxMDMwMjM1OTU5WjB+MQsw
CQYDVQQGEwJVUzEdMBsGA1UEChMUU3ltYW50ZWMgQ29ycG9yYXRpb24xHzAdBgNV
BAsTFlN5bWFudGVjIFRydXN0IE5ldHdvcmsxLzAtBgNVBAMTJlN5bWFudGVjIENs
YXNzIDMgU2VjdXJlIFNlcnZlciBDQSAtIEc0MIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEAstgFyhx0LbUXVjnFSlIJluhL2AzxaJ+aQihiw6UwU35VEYJb
A3oNL+F5BMm0lncZgQGUWfm893qZJ4Itt4PdWid/sgN6nFMl6UgfRk/InSn4vnlW
9vf92Tpo2otLgjNBEsPIPMzWlnqEIRoiBAMnF4scaGGTDw5RgDMdtLXO637QYqzu
s3sBdO9pNevK1T2p7peYyo2qRA4lmUoVlqTObQJUHypqJuIGOmNIrLRM0XWTUP8T
L9ba4cYY9Z/JJV3zADreJk20KQnNDz0jbxZKgRb78oMQw7jW2FUyPfG9D72MUpVK
Fpd6UiFjdS8W+cRmvvW1Cdj/JwDNRHxvSz+w9wIDAQABo4IBYzCCAV8wEgYDVR0T
AQH/BAgwBgEB/wIBADAwBgNVHR8EKTAnMCWgI6Ahhh9odHRwOi8vczEuc3ltY2Iu
Y29tL3BjYTMtZzUuY3JsMA4GA1UdDwEB/wQEAwIBBjAvBggrBgEFBQcBAQQjMCEw
HwYIKwYBBQUHMAGGE2h0dHA6Ly9zMi5zeW1jYi5jb20wawYDVR0gBGQwYjBgBgpg
hkgBhvhFAQc2MFIwJgYIKwYBBQUHAgEWGmh0dHA6Ly93d3cuc3ltYXV0aC5jb20v
Y3BzMCgGCCsGAQUFBwICMBwaGmh0dHA6Ly93d3cuc3ltYXV0aC5jb20vcnBhMCkG
A1UdEQQiMCCkHjAcMRowGAYDVQQDExFTeW1hbnRlY1BLSS0xLTUzNDAdBgNVHQ4E
FgQUX2DPYZBV34RDFIpgKrL1evRDGO8wHwYDVR0jBBgwFoAUf9Nlp8Ld7LvwMAnz
Qzn6Aq8zMTMwDQYJKoZIhvcNAQELBQADggEBAF6UVkndji1l9cE2UbYD49qecxny
H1mrWH5sJgUs+oHXXCMXIiw3k/eG7IXmsKP9H+IyqEVv4dn7ua/ScKAyQmW/hP4W
Ko8/xabWo5N9Q+l0IZE1KPRj6S7t9/Vcf0uatSDpCr3gRRAMFJSaXaXjS5HoJJtG
QGX0InLNmfiIEfXzf+YzguaoxX7+0AjiJVgIcWjmzaLmFN5OUiQt/eV5E1PnXi8t
TRttQBVSK/eHiXgSgW7ZTaoteNTCLD0IX4eRnh8OsN4wUmSGiaqdZpwOdgyA8nTY
Kvi4Os7X1g8RvmurFPW9QaAiY4nxug9vKWNmLT+sjHLF+8fk1A/yO0+MKcc=
-----END CERTIFICATE-----`

func init() {
	pflag.StringVar(&options.KubeConfig, "kubeconfig", "", "Path to kubeconfig file with authorization and master location information.")
	pflag.StringVar(&options.ViceCrtFile, "vice-cert", "", "A PEM eoncoded certificate file.")
	pflag.StringVar(&options.ViceKeyFile, "vice-key", "", "A PEM encoded private key file.")
}

func main2() {
	// Set logging output to standard console out 
	log.SetOutput(os.Stdout)

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	sigs := make(chan os.Signal, 1)
	stop := make(chan struct{})
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM) // Push signals into channel

	wg := &sync.WaitGroup{} // Goroutines can add themselves to this to be waited on

	go president.New(options).Run(10, stop, wg)

	<-sigs // Wait for signals (this hangs until a signal arrives)
	log.Printf("Shutting down...")

	close(stop) // Tell goroutines to stop themselves
	wg.Wait()   // Wait for all to be stopped
}

func main3() {
	// Set logging output to standard console out
	log.SetOutput(os.Stdout)

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	viceClient := NewViceClient(options)

	ctx := context.TODO()
	enrollRequest := &vice.EnrollRequest{
		Challenge:       "Hase",
		CertProductType: vice.CertProductType.Server,
		FirstName:       "Michael",
		MiddleInitial:   "J",
		LastName:        "Schmidt",
		Email:           "michael02.schmidt@sap.com",
		CSR: `-----BEGIN CERTIFICATE REQUEST-----
MIIC/TCCAeUCAQAwfjELMAkGA1UEBhMCREUxETAPBgNVBAcMCFdhbGxkb3JmMQ8w
DQYDVQQKDAZTQVAgU0UxJDAiBgNVBAsMG0luZnJhc3RydWN0dXJlIEF1dG9taXph
dGlvbjElMCMGA1UEAwwcZGVsZXRlbWUwMC5ldS1kZS0xLmNsb3VkLnNhcDCCASIw
DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANbQi/iSUTPsvQ7/l/2mbJx7kuzR
4kiWq2EJsKFD6wfAHZTRTToH7wrmwGLzo778FJuvPImhnbZUmLM1oBmA4tETftbG
AdlDQB2d8jBA+n3CVaXqKTkVxbYkqupKtPF2ynUqLoszjw8bkFE/LDyokHWsLzAp
VLxeoM3RLPvL+7JcOr9bHiFWYl935SDqi1em1wfUZm24GrDQO0rM8E7I+Ftu3K76
dviV7X6w7c2GtR803gsHP4ZeyI125Up/G/cAxtqqWBpg4SH0eQOcc3Y73M7bkCYh
k0leXLPy7rt+RZNLB5AVBvsdy61eYzb6lkXKOhGMCyRpTMXPrkSHb7k2+5sCAwEA
AaA6MDgGCSqGSIb3DQEJDjErMCkwJwYDVR0RBCAwHoIcZGVsZXRlbWUwMC5ldS1k
ZS0xLmNsb3VkLnNhcDANBgkqhkiG9w0BAQsFAAOCAQEAPc112rqUQDQ77Z309Y3T
DCn4pjHp40pACjp5PGt34pLTBTrIhrktc3X0uYkm4y7k345qZFKvYVBiUqwokMw1
WLNoBDKD7Qd0SMCjZblzpfHma5uizA9uA4JZ5LkPf6gjkCISzBu5pvFjJZMzRGFQ
vNTO9ILAltFXCiiB/zoFv/nJ501fxztxBwf9RTNkAFXCxpAZcTyKB6AxFRT0svfd
SN39EDpm3rucXQwasnRsz0tgO7aTO/XBs5bDENCEPqV1e4Qu+sPXTfB2oqz5mGz9
TarAKeFZYCecSJif9sHegvTexS4HfXWt1xZYju29bVAEAB6Qg3JCvcqF/kNHQzBX
Tg==
-----END CERTIFICATE REQUEST-----`,
		ServerType:         vice.ServerType.OpenSSL,
		SpecificEndDate:    vice.Date{time.Now().AddDate(0, 1, 0)},
		EmployeeId:         "d038720",
		SignatureAlgorithm: vice.SignatureAlgorithm.SHA256WithRSAEncryption,
		SubjectAltNames:    []string{"deletmetoo.eu-de-1.cloud.sap", "mefirst.eu-de-1.cloud.sap"},
		AdditionalFields:   []string{"0123456789", "abc123"},
	}
	_, err := viceClient.Certificates.Enroll(ctx, enrollRequest)
	if err != nil {
		glog.Errorf("%s", err)
	}
}

func NewViceClient(options president.Options) *vice.Client {
	cert, err := tls.LoadX509KeyPair(options.ViceCrtFile, options.ViceKeyFile)
	if err != nil {
		log.Fatal(err)
	}

	return vice.New(cert)
}

func main() {
	// Set logging output to standard console out
	log.SetOutput(os.Stdout)

	pflag.CommandLine.AddGoFlagSet(flag.CommandLine)
	pflag.Parse()

	path := "/Users/d038720/Code/sapcc/secrets/eu-nl-1/certificates"

	requestCerts(regions.NL, path)
	renewCerts(regions.NL, path)
	approveCerts(regions.NL, path)
	fetchCerts(regions.NL, path)
}

func renewCerts(certs []regions.CertificateRequest, path string) {
	glog.Info("============================================================================")
	glog.Info("  Renewing Expired Certificates")
	glog.Info("============================================================================")

	for _, cr := range certs {
		basename := filepath.Join(path, cr.CN)

		raw, err := readCert(basename)
		if err != nil {
			glog.Errorf("Couldn't read certificate for %v: %v", cr.CN, err)
			continue
		}

		block, _ := pem.Decode([]byte(raw))
		cert, err := x509.ParseCertificate(block.Bytes)
		if err != nil {
			glog.Errorf("Couldn't parse certificate for %v: %v", cr.CN, err)
			continue
		}

		glog.V(5).Infof("Certificate %v is valid until %v", cr.CN, cert.NotAfter)

		pool := x509.NewCertPool()
		pool.AppendCertsFromPEM([]byte(SYMANTEC_INTERMEDIATE))

		opts := x509.VerifyOptions{
			CurrentTime:   time.Now().AddDate(0, 1, 0),
			Intermediates: pool,
		}

		_, err = cert.Verify(opts)
		if err == nil {
			glog.V(3).Infof("Certificate is valid. %v: %v", cr.CN, err)
		} else {
			glog.Info("Certificate is expiring soon: %v: %v", cr.CN, err)
		}

	}
}

func approveCerts(certs []regions.CertificateRequest, path string) {
	glog.Info("============================================================================")
	glog.Info("  Approving Certificates")
	glog.Info("============================================================================")

	viceClient := NewViceClient(options)

	for _, cr := range certs {
		basename := filepath.Join(path, cr.CN)

		tid, err := readTID(basename)
		if err != nil {
			glog.V(5).Infof("Skipping approval of %v. No TID found", cr.CN)
			continue
		}

		glog.V(5).Infof("Approving %v in transaction %v", cr.CN, tid)
		approval, err := viceClient.Certificates.Approve(context.TODO(), &vice.ApprovalRequest{TransactionID: tid})

		if err != nil {
			glog.Errorf("Couldn't approve certificate for transaction %v: %v", tid, err)
			continue
		}

		err = writeCert(basename, approval.Certificate)
		if err != nil {
			glog.Errorf("Couldn't write cert: %v", err)
		}

		glog.Infof("Picked up certificate for %v", cr.CN)
		err = deleteTID(basename)
		if err != nil {
			glog.Errorf("Couldn't delete tid: %v", err)
		}

		err = appendIntermediateCert(basename, SYMANTEC_INTERMEDIATE)

		if err != nil {
			glog.Errorf("Couldn't append intermediate: %v", err)
		}
	}
}

func fetchCerts(certs []regions.CertificateRequest, path string) {
	glog.Info("============================================================================")
	glog.Info("  Fetching Certificates")
	glog.Info("============================================================================")

	viceClient := NewViceClient(options)

	for _, cr := range certs {
		basename := filepath.Join(path, cr.CN)

		tid, err := readTID(basename)
		if err != nil {
			glog.V(5).Infof("Skipping download of %v. No TID found", cr.CN)
			continue
		}

		glog.V(5).Infof("Fetching certificate %v in transaction %v", cr.CN, tid)
		pickup, err := viceClient.Certificates.Pickup(context.TODO(), &vice.PickupRequest{TransactionID: tid})

		if err != nil {
			glog.Errorf("Couldn't pickup certificate for transaction %v: %v", tid, err)
			continue
		}

		err = writeCert(basename, pickup.Certificate)
		if err != nil {
			glog.Errorf("Couldn't write cert: %v", err)
		}

		glog.Infof("Picked up certificate for %v", cr.CN)
		err = deleteTID(basename)
		if err != nil {
			glog.Errorf("Couldn't delete tid: %v", err)
		}

		err = appendIntermediateCert(basename, SYMANTEC_INTERMEDIATE)

		if err != nil {
			glog.Errorf("Couldn't append intermediate: %v", err)
		}
	}

	glog.Info("")
}

func requestCerts(certs []regions.CertificateRequest, path string) {
	viceClient := NewViceClient(options)
	glog.Info("============================================================================")
	glog.Info("  Requesting Certificates")
	glog.Info("============================================================================")

	for _, cr := range certs {
		basename := filepath.Join(path, cr.CN)

		tid, err := readTID(basename)
		if tid != "" {
			glog.Infof("Pending certificate for %v. Skipping...", cr.CN)
			continue
		}

		_, err = readCert(basename)
		if err == nil {
			glog.Infof("Existing certificate for %v. Skipping...", cr.CN)
			continue
		}

		glog.Infof("Enrolling certificate for %v.", cr.CN)

		key, _, err := readKey(basename)
		if err != nil {
			glog.Fatalf("Key failed: %v", err)
		}

		csr, err := newRawCSR(cr.CN, cr.SANS, key)
		if err != nil {
			glog.Fatalf("Generating CSR failed: %v", err)
		}

		err = writeCSR(basename, csr)
		if err != nil {
			glog.Fatalf("Writing CSR failed: %v", err)
		}

		enrollRequest := &vice.EnrollRequest{
			Challenge:          "Mo10.Ch7",
			CertProductType:    vice.CertProductType.Server,
			FirstName:          "Michael",
			MiddleInitial:      "J",
			LastName:           "Schmidt",
			Email:              "michael02.schmidt@sap.com",
			CSR:                string(csr),
			ServerType:         vice.ServerType.OpenSSL,
			EmployeeId:         "d038720",
			SignatureAlgorithm: vice.SignatureAlgorithm.SHA256WithRSAEncryption,
			SubjectAltNames:    cr.SANS,
			ValidityPeriod:     vice.ValidityPeriod.OneYear,
		}

		ctx := context.TODO()
		enrollment, err := viceClient.Certificates.Enroll(ctx, enrollRequest)
		if err != nil {
			glog.Errorf("%s", err)
			continue
		} else {
			err = writeTID(basename, enrollment.TransactionID)
			if err != nil {
				glog.Fatalf("Writing TID failed: %v", err)
			}
		}
	}

	glog.Info("")
}

func readKey(basename string) (key *rsa.PrivateKey, pem []byte, err error) {
	file := fmt.Sprintf("%s-key.pem", basename)

	if _, err = os.Stat(file); !os.IsNotExist(err) {
		pem, err = ioutil.ReadFile(file)
		if err == nil {
			key, err = x509.ParsePKCS1PrivateKey(pem)
		}
	} else {
		key, pem, err = newRSAKey()
		if err == nil {
			err = writeKey(basename, pem)
		}
	}

	return
}

func readTID(basename string) (string, error) {
	file := fmt.Sprintf("%s.tid", basename)

	if _, err := os.Stat(file); os.IsNotExist(err) {
		return "", fmt.Errorf("No TID found")
	}

	tid, err := ioutil.ReadFile(file)
	if err != nil {
		return "", err
	}

	return string(tid), nil
}

func writeKey(basename string, pem []byte) error {
	return ioutil.WriteFile(fmt.Sprintf("%s-key.pem", basename), pem, 0644)
}

func writeTID(basename, tid string) error {
	return ioutil.WriteFile(fmt.Sprintf("%s.tid", basename), []byte(tid), 0644)
}

func deleteTID(basename string) error {
	return os.Remove(fmt.Sprintf("%s.tid", basename))
}

func writeCSR(basename string, pem []byte) error {
	return ioutil.WriteFile(fmt.Sprintf("%s.csr", basename), pem, 0644)
}

func writeCert(basename, pem string) error {
	return ioutil.WriteFile(fmt.Sprintf("%s.pem", basename), []byte(pem), 0644)
}

func readCert(basename string) (string, error) {
	file := fmt.Sprintf("%s.pem", basename)

	if _, err := os.Stat(file); os.IsNotExist(err) {
		return "", fmt.Errorf("No PEM found")
	}

	pem, err := ioutil.ReadFile(file)
	if err != nil {
		return "", err
	}

	return string(pem), nil
}

func appendIntermediateCert(basename, pem string) error {
	f, err := os.OpenFile(fmt.Sprintf("%s.pem", basename), os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}

	defer f.Close()

	if _, err = f.WriteString(pem); err != nil {
		return err
	}

	return nil
}

func newRSAKey() (*rsa.PrivateKey, []byte, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, nil, err
	}

	block := pem.Block{
		Type:    "RSA PRIVATE KEY",
		Headers: nil,
		Bytes:   x509.MarshalPKCS1PrivateKey(key),
	}

	return key, pem.EncodeToMemory(&block), nil
}

func newRawCSR(commonName string, sans []string, key *rsa.PrivateKey) ([]byte, error) {
	email := "michael02.schmidt@sap.com"

	name := pkix.Name{
		CommonName:         commonName,
		Country:            []string{"DE"},
		Province:           []string{"BERLIN"},
		Locality:           []string{"BERLIN"},
		Organization:       []string{"SAP SE"},
		OrganizationalUnit: []string{"Infrastructure Automization"},
	}

	return vice.CreateCSR(name, email, sans, key)
}
