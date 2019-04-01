package president

import (
	"crypto/rsa"
	"crypto/x509"
	"fmt"
	"reflect"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/pkg/api"
	"k8s.io/client-go/pkg/api/v1"
)

func newEmptySecret(nameSpace, name string, labels map[string]string) *v1.Secret {
	if labels == nil {
		labels = map[string]string{}
	}
	return &v1.Secret{
		ObjectMeta: meta_v1.ObjectMeta{
			Name:      name,
			Namespace: nameSpace,
			Labels:    labels,
		},
		Type: v1.SecretTypeOpaque,
	}
}

// GetCertificateAndKeyFromSecret extracts the certificate and private key from a given secrets spec
func getCertificateAndKeyFromSecret(secret *v1.Secret, tlsKeySecretKey, tlsCertSecretKey string) (*x509.Certificate, *rsa.PrivateKey, error) {
	var (
		certificate *x509.Certificate
		privateKey  *rsa.PrivateKey
	)

	if secret.Data == nil {
		return nil, nil, fmt.Errorf("secret %s/%s is empty", secret.GetNamespace(), secret.GetName())
	}

	if k, ok := secret.Data[tlsKeySecretKey]; ok && len(k) > 0 {
		key, err := readPrivateKeyFromPEM(k)
		if err != nil {
			return nil, nil, fmt.Errorf("no tls key found in secret %s/%s", secret.GetNamespace(), secret.GetName())
		}
		privateKey = key
	}

	// key exists and we might be able to pickup the certificate.
	if c, ok := secret.Data[tlsCertSecretKey]; ok && len(c) > 0 {
		cert, err := readCertificateFromPEM(c)
		if err != nil {
			return nil, privateKey, err
		}
		certificate = cert
	}

	if certificate == nil && privateKey == nil {
		return nil, nil, fmt.Errorf("neither certificate nor private key found in secret: %s/%s", secret.Namespace, secret.Name)
	}

	return certificate, privateKey, nil
}

func addCertificateAndKeyToSecret(viceCert *ViceCertificate, oldSecret *v1.Secret, tlsKeySecretKey, tlsCertSecretKey string) (*v1.Secret, error) {
	certPEM, err := writeCertificatesToPEM(viceCert.withIntermediateCertificate())
	if err != nil {
		return nil, err
	}
	keyPEM, err := writePrivateKeyToPEM(viceCert.privateKey)
	if err != nil {
		return nil, err
	}

	o, err := api.Scheme.Copy(oldSecret)
	if err != nil {
		return nil, err
	}
	secret := o.(*v1.Secret)

	if secret.Data == nil {
		secret.Data = map[string][]byte{}
	}

	secret.Data[tlsCertSecretKey] = removeSpecialCharactersFromPEM(certPEM)
	secret.Data[tlsKeySecretKey] = removeSpecialCharactersFromPEM(keyPEM)

	return secret, nil
}

func isSecretNeedsUpdate(sCur, sOld *v1.Secret) bool {
	// make sure to only trigger an update there are no empty values.
	// the ingress controller doesn't like this.
	for _, v := range sCur.Data {
		if v == nil {
			return false
		}
	}
	if !reflect.DeepEqual(sOld.Data, sCur.Data) {
		return true
	}
	return false
}

func isSecretExists(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apierrors.NewNotFound(schema.GroupResource{Resource: "secret"}, "")
	case watch.Added:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func isSecretDeleted(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return true, nil
	default:
		return false, nil
	}
	return false, nil
}

func secretKey(ingressNamespace, secretName string) string {
	return fmt.Sprintf("%s/%s", ingressNamespace, secretName)
}
