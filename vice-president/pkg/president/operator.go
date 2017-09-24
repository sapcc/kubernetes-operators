/*******************************************************************************
*
* Copyright 2017 SAP SE
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You should have received a copy of the License along with this
* program. If not, you may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
*******************************************************************************/

package president

import (
	"sync"
	"time"

	"crypto/x509"

	"crypto/tls"

	"fmt"
	"reflect"

	"strings"

	"bytes"
	"crypto/rsa"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/go-vice"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/pkg/api"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

var (
	// VERSION of the vice president
	VERSION = "0.0.0.dev"
	// ResyncPeriod defines the period after which down- and upstream are synced
	ResyncPeriod = 10 * time.Second
	// CertificateRecheckInterval defines the period after which certificates are checked
	// A minimum of 60 seconds is necessary
	CertificateRecheckInterval = 60 * time.Second
)

// Operator is the vice-president certificate operator
type Operator struct {
	Options

	VicePresidentConfig VicePresidentConfig

	Clientset       *kubernetes.Clientset
	ViceClient      *vice.Client
	IngressInformer cache.SharedIndexInformer
	SecretInformer  cache.SharedIndexInformer

	rootCertPool *x509.CertPool

	queue workqueue.RateLimitingInterface
}

// New creates a new operator using the given options
func New(options Options) *Operator {

	LogInfo("Creating new vice president in version %v\n", VERSION)

	if err := options.CheckOptions(); err != nil {
		LogInfo(err.Error())
	}

	config := newClientConfig(options)

	vicePresidentConfig, err := ReadConfig(options.VicePresidentConfig)
	if err != nil {
		LogFatal("Could get vice configuration: %s. Aborting.", err)
	}

	if vicePresidentConfig.ResyncPeriod != 0 {
		ResyncPeriod = time.Duration(vicePresidentConfig.ResyncPeriod) * time.Second
	}

	if vicePresidentConfig.CertificateCheckInterval != 0 {
		CertificateRecheckInterval = time.Duration(vicePresidentConfig.CertificateCheckInterval) * time.Second
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		LogFatal("Couldn't create Kubernetes client: %s", err)
	}

	cert, err := tls.LoadX509KeyPair(options.ViceCrtFile, options.ViceKeyFile)
	if err != nil {
		LogFatal("Couldn't load certificate from %s and/or key from %s for vice client %s", options.ViceCrtFile, options.ViceKeyFile, err)
	}
	viceClient := vice.New(cert)
	if viceClient == nil {
		LogFatal("Couldn't create vice client: %s", err)
	}

	caCert, err := readCertFromFile(options.ViceCrtFile)
	if err != nil {
		LogFatal("Couldn't read CA Cert. Aborting.")
	}
	rootCertPool := x509.NewCertPool()
	rootCertPool.AddCert(caCert)

	operator := &Operator{
		Options:             options,
		Clientset:           clientset,
		VicePresidentConfig: vicePresidentConfig,
		ViceClient:          viceClient,
		rootCertPool:        rootCertPool,
		queue:               workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
	}

	IngressInformer := cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options meta_v1.ListOptions) (runtime.Object, error) {
				return clientset.Ingresses(v1.NamespaceAll).List(meta_v1.ListOptions{})
			},
			WatchFunc: func(options meta_v1.ListOptions) (watch.Interface, error) {
				return clientset.Ingresses(v1.NamespaceAll).Watch(meta_v1.ListOptions{})
			},
		},
		&v1beta1.Ingress{},
		ResyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	SecretInformer := cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options meta_v1.ListOptions) (runtime.Object, error) {
				return clientset.Secrets(v1.NamespaceAll).List(meta_v1.ListOptions{})
			},
			WatchFunc: func(options meta_v1.ListOptions) (watch.Interface, error) {
				return clientset.Secrets(v1.NamespaceAll).Watch(meta_v1.ListOptions{})
			},
		},
		&v1.Secret{},
		ResyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	IngressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.ingressAdd,
		UpdateFunc: operator.ingressUpdate,
		DeleteFunc: operator.ingressDelete,
	})

	SecretInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.secretAdd,
		UpdateFunc: operator.secretUpdate,
		DeleteFunc: operator.secretDelete,
	})

	operator.IngressInformer = IngressInformer
	operator.SecretInformer = SecretInformer

	return operator
}

// Run starts the operator
func (vp *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer utilruntime.HandleCrash()
	defer vp.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)

	LogInfo("Ladies and Gentlemen, the Vice President! Renewing your Symantec certificates now in version %v\n", VERSION)

	go vp.IngressInformer.Run(stopCh)
	go vp.SecretInformer.Run(stopCh)

	LogInfo("Waiting for cache to sync...")
	cache.WaitForCacheSync(
		stopCh, vp.IngressInformer.HasSynced,
		vp.SecretInformer.HasSynced,
	)
	LogInfo("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(vp.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(CertificateRecheckInterval)
	go func() {
		for {
			select {
			case <-ticker.C:
				LogInfo("Next check in %v", CertificateRecheckInterval)
				vp.checkCertificates()
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
}

func (vp *Operator) runWorker() {
	for vp.processNextWorkItem() {
	}
}

func (vp *Operator) processNextWorkItem() bool {
	key, quit := vp.queue.Get()
	if quit {
		return false
	}
	defer vp.queue.Done(key)

	// do your work on the key.  This method will contains your "do stuff" logic
	err := vp.syncHandler(key)
	if err == nil {
		vp.queue.Forget(key)
		return true
	}

	LogError("%v failed with : %v", key, err)
	vp.queue.AddRateLimited(key)

	return true
}

func (vp *Operator) syncHandler(key interface{}) error {
	o, exists, err := vp.IngressInformer.GetStore().Get(key)
	if checkError(err) != nil {
		utilruntime.HandleError(fmt.Errorf("%v failed with : %v", key, err))
		return err
	}

	if !exists {
		LogInfo("Deleted ingress %#v", key)
		return nil
	}

	ingress := o.(*v1beta1.Ingress)

	if vp.isTakeCareOfIngress(ingress) {

		for _, tls := range ingress.Spec.TLS {

			LogInfo("Checking Ingress %v/%v: Hosts: %v, Secret: %v/%v", ingress.GetNamespace(), ingress.GetName(), tls.Hosts, ingress.GetNamespace(), tls.SecretName)

			for _, host := range tls.Hosts {
				if err := vp.runStateMachine(ingress, tls.SecretName, host); err != nil {
					return err
				}
			}
		}
	} else {
		LogDebug("Ignoring ingress %v/%v as vice-presidential annotation was not set.", ingress.GetNamespace(), ingress.GetName())
	}
	return err
}

func (vp *Operator) runStateMachine(ingress *v1beta1.Ingress, secretName, host string) error {
	// labels for prometheus metrics
	labels := prometheus.Labels{
		"ingress": fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName()),
		"host":    host,
	}
	// add 0 to initialize the metrics that indicate failure
	initializeFailureMetrics(labels)

	var viceCert *ViceCertificate
	var secret *v1.Secret
	var state, nextState string

	for {
		// return an error if something is off to avoid a constant loop and give another ingress a chance
		state = nextState
		LogDebug("Setting state: %s", state)

		switch state {
		case IngressStateEnroll:
			if err := vp.enrollCertificate(viceCert); err != nil {
				LogInfo("Couldn't enroll new certificate for ingress %s/%s and host %s: %s", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, err)

				enrollFailedCounter.With(labels).Inc()

				return err
			}
			enrollSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateRenew:
			if err := vp.renewCertificate(viceCert); err != nil {
				LogInfo("Couldn't renew certificate for ingress %s/%s, host %s using TID %s: %s.", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, viceCert.TID, err)

				renewFailedCounter.With(labels).Inc()

				return err
			}

			renewSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateApprove:
			if viceCert.Certificate != nil {
				LogInfo("Certificate for ingress %s/%s, host %s was automatically approved", ingress.GetNamespace(), ingress.GetName(), viceCert.Host)
			} else {
				if err := vp.approveCertificate(viceCert); err != nil {
					LogInfo("Couldn't approve certificate for ingress %s/%s, host %s using TID %s: %s", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, viceCert.TID, err)
					approveFailedCounter.With(labels).Inc()
					return err
				}
			}

			if err := vp.updateCertificateAndKeyInSecret(secret, viceCert); err != nil {
				return err
			}

			approveSuccessCounter.With(labels).Inc()

			nextState = IngressStateApproved

		case IngressStatePickup:
			if err := vp.pickupCertificate(viceCert); err != nil {
				LogInfo("Couldn't pickup certificate for ingress %s/%s, host %s using TID %s: %s.", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, viceCert.TID, err)

				pickupFailedCounter.With(labels).Inc()

				return err
			}

			pickupSuccessCounter.With(labels).Inc()

			if err := vp.updateCertificateAndKeyInSecret(secret, viceCert); err != nil {
				return err
			}

			nextState = IngressStateApprove

		case IngressStateApproved:
			return nil

		default:
			// check the secret. does it exist? does it contain a certificate and a key?
			// if not create empty secret in namespace of ingress and set to enrolling state
			v, s, err := vp.checkSecret(ingress, host, secretName)
			if err != nil || v.Certificate == nil {
				nextState = IngressStateEnroll
			}
			viceCert = v
			secret = s

			// if a certificate was found, validate it
			if viceCert.Certificate != nil {
				nextState = vp.checkViceCertificate(viceCert)
			}
		}

	}
	return nil
}

func (vp *Operator) isTakeCareOfIngress(ingress *v1beta1.Ingress) bool {
	if ingress.GetAnnotations()[vp.Options.IngressAnnotation] == "true" {
		return true
	}
	return false
}

func (vp *Operator) checkSecret(ingress *v1beta1.Ingress, host, secretName string) (*ViceCertificate, *v1.Secret, error) {

	// force sync here
	if err := vp.SecretInformer.GetStore().Resync(); err != nil {
		return nil, nil, err
	}

	obj, exists, err := vp.SecretInformer.GetStore().GetByKey(fmt.Sprintf("%s/%s", ingress.GetNamespace(), secretName))

	// does the secret exist?
	if !exists || (err != nil && apierrors.IsNotFound(err)) {
		LogInfo("Secret %s/%s doesn't exist. Creating it and enrolling certificate", ingress.GetNamespace(), secretName)
		secret := vp.createEmptySecret(ingress.GetNamespace(), secretName)
		if err := vp.addUpstreamSecret(secret); err != nil {
			return &ViceCertificate{Host: host, Roots: vp.rootCertPool}, secret, err
		}
		return &ViceCertificate{Host: host, Roots: vp.rootCertPool}, secret, nil
	}

	if checkError(err) != nil {
		LogInfo("Couldn't get secret %s/%s.", ingress.GetNamespace(), secretName)
		return &ViceCertificate{Host: host, Roots: vp.rootCertPool}, &v1.Secret{}, err
	}

	secret := obj.(*v1.Secret)

	// does the certificate exist? can it be decoded and parsed from the secret?
	cert, key, err := vp.getCertificateAndKeyFromSecret(secret)
	if err != nil {
		LogError(err.Error())
		return &ViceCertificate{Host: host, Roots: vp.rootCertPool}, secret, nil
	}
	return &ViceCertificate{Host: host, Roots: vp.rootCertPool, Certificate: cert, PrivateKey: key}, secret, nil
}

// checkViceCertificate checks a given ViceCertificate and annotates the ingress accordingly
func (vp *Operator) checkViceCertificate(viceCert *ViceCertificate) string {
	// does the secret contain the correct key for the certificate?
	if !viceCert.DoesKeyAndCertificateTally() {
		LogInfo("Certificate and Key don't match. Renewing")
		return IngressStateRenew
	}

	//  is the certificate for the correct host?
	if !viceCert.DoesCertificateAndHostMatch() {
		LogInfo("Certificate and Host don't match. Enrolling new one")
		return IngressStateEnroll
	}

	// is the certificate valid for time t ?
	if viceCert.DoesCertificateExpireSoon() {
		LogInfo("Certificate for host %s will expire in %s month. Renewing", viceCert.Host, CertificateRecheckInterval)
		return IngressStateRenew
	}
	LogInfo("Certificate for host %s is valid until %s", viceCert.Host, viceCert.Certificate.NotAfter.UTC())
	return IngressStateApproved
}

// UpdateCertificateInSecret adds or updates the certificate in a secret
func (vp *Operator) updateCertificateAndKeyInSecret(secret *v1.Secret, vc *ViceCertificate) error {
	LogInfo("Add/Update certificate and key in secret %s/%s", secret.GetNamespace(), secret.GetName())
	updatedSecret, err := vp.addCertificateAndKeyToSecret(vc, secret)
	if err != nil {
		LogError("Couldn't update secret %s/%s: %s", secret.Namespace, secret.Name, err)
		return err
	}
	if err := vp.updateUpstreamSecret(updatedSecret, secret); err != nil {
		return err
	}
	return nil
}

// EnrollCertificate triggers the enrollment of a certificate
func (vp *Operator) enrollCertificate(vc *ViceCertificate) error {
	if err := vc.enroll(vp); err != nil {
		LogError("Couldn't enroll certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// RenewCertificate triggers the renewal of a certificate
func (vp *Operator) renewCertificate(vc *ViceCertificate) error {
	if err := vc.renew(vp); err != nil {
		LogError("Couldn't renew certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// ApproveCertificate triggers the approval of a certificate
func (vp *Operator) approveCertificate(vc *ViceCertificate) error {
	if err := vc.approve(vp); err != nil {
		LogError("Couldn't approve certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// PickupCertificate picks up a given certificate
func (vp *Operator) pickupCertificate(vc *ViceCertificate) error {
	if err := vc.pickup(vp); err != nil {
		LogError("Couldn't approve certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

func (vp *Operator) createEmptySecret(nameSpace, secretName string) *v1.Secret {
	return &v1.Secret{
		ObjectMeta: meta_v1.ObjectMeta{
			Name:      secretName,
			Namespace: nameSpace,
		},
		Type: v1.SecretTypeOpaque,
	}
}

// GetCertificateAndKeyFromSecret extracts the certificate and private key from a given secrets spec
func (vp *Operator) getCertificateAndKeyFromSecret(secret *v1.Secret) (*x509.Certificate, *rsa.PrivateKey, error) {
	var certificate *x509.Certificate
	var privateKey *rsa.PrivateKey
	// do not just return on error. we might be able to pickup the certificate if the key still exists.
	if secret.Data != nil {
		for k, v := range secret.Data {
			// force tls_cert to tls.cert | force tls_key to tls.key
			k = strings.Replace(k, "_", ".", -1)
			// force tls.cert to tls.crt
			k = strings.Replace(k, "cert", "crt", -1)
			switch k {
			case SecretTLSCertType:
				if v == nil || len(v) == 0 {
					LogInfo("Certificate in secret %s/%s is empty", secret.GetNamespace(), secret.GetName())
					continue
				}
				c, err := readCertificateFromPEM(v)
				if err != nil {
					LogError(err.Error())
				}
				certificate = c
			case SecretTLSKeyType:
				if v == nil || len(v) == 0 {
					LogInfo("Key in secret %s/%s is empty", secret.GetNamespace(), secret.GetName())
					continue
				}
				k, err := readPrivateKeyFromPEM(v)
				if err != nil {
					LogError(err.Error())
				}
				privateKey = k
			}
		}
	}
	if certificate == nil && privateKey == nil {
		return nil, nil, fmt.Errorf("Neither certificate nor private key found in secret: %s/%s", secret.Namespace, secret.Name)
	}
	return certificate, privateKey, nil
}

func (vp *Operator) addCertificateAndKeyToSecret(viceCert *ViceCertificate, oldSecret *v1.Secret) (*v1.Secret, error) {

	certPEM, err := writeCertificateToPEM(viceCert.Certificate)
	if err != nil {
		LogError("Couldn't export certificate to PEM: %s", err)
		return nil, err
	}
	keyPEM, err := writePrivateKeyToPEM(viceCert.PrivateKey)
	if err != nil {
		LogError("Couldn't export key to PEM: %s", err)
		return nil, err
	}

	o, err := api.Scheme.Copy(oldSecret)
	if checkError(err) != nil {
		return nil, err
	}
	secret := o.(*v1.Secret)

	if secret.Data == nil {
		secret.Data = map[string][]byte{}
	}

	secret.Data[SecretTLSCertType] = bytes.Trim(certPEM, "\"")
	secret.Data[SecretTLSKeyType] = bytes.Trim(keyPEM, "\"")

	return secret, nil
}

// IsIngressNeedsUpdate determines whether an ingress is outdated an should be updated
func (vp *Operator) isIngressNeedsUpdate(iCur, iOld *v1beta1.Ingress) bool {
	if !reflect.DeepEqual(iOld.Spec, iCur.Spec) || !reflect.DeepEqual(iOld.GetAnnotations(), iCur.GetAnnotations()) {
		return true
	}
	return false
}

func (vp *Operator) isSecretNeedsUpdate(sCur, sOld *v1.Secret) bool {
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

func (vp *Operator) ingressAdd(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	vp.queue.Add(i)
}

func (vp *Operator) ingressDelete(obj interface{}) {
	i, ok := obj.(*v1beta1.Ingress)
	if !ok {
		// If we reached here it means the ingress was deleted but its final state is unrecorded.
		tombstone, ok := obj.(cache.DeletedFinalStateUnknown)
		if !ok {
			LogError("Couldn't get object from tombstone %#v", obj)
			return
		}
		_, ok = tombstone.Obj.(*v1beta1.Ingress)
		if !ok {
			LogError("Tombstone contained object that is not an Ingress: %#v", obj)
			return
		}
	}
	LogDebug("Deleted ingress %s/%s.", i.GetNamespace(), i.GetName())
	key, err := cache.DeletionHandlingMetaNamespaceKeyFunc(i)
	if err != nil {
		return
	}
	vp.queue.Add(key)

}

func (vp *Operator) ingressUpdate(cur, old interface{}) {
	iOld := old.(*v1beta1.Ingress)
	iCur := cur.(*v1beta1.Ingress)

	if vp.isIngressNeedsUpdate(iCur, iOld) {
		LogDebug("Updated ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		vp.queue.Add(iCur)
		return
	}
	LogDebug("Nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
}

func (vp *Operator) secretAdd(obj interface{}) {
	s := obj.(*v1.Secret)
	vp.SecretInformer.GetStore().Add(s)
}

func (vp *Operator) secretUpdate(cur, old interface{}) {
	sOld := old.(*v1.Secret)
	sCur := cur.(*v1.Secret)

	if vp.isSecretNeedsUpdate(sCur, sOld) {
		LogDebug("Updated secret %s/%s", sOld.GetNamespace(), sOld.GetName())
		vp.SecretInformer.GetStore().Update(sCur)
		return
	}
	LogDebug("Nothing changed. No need to update secret %s/%s", sOld.GetNamespace(), sOld.GetName())
}

func (vp *Operator) secretDelete(obj interface{}) {
	s := obj.(*v1.Secret)
	vp.SecretInformer.GetStore().Delete(s)
	LogDebug("Deleted secret %s/%s.", s.GetNamespace(), s.GetName())
}

func (vp *Operator) addUpstreamSecret(secret *v1.Secret) error {
	LogInfo("Added upstream secret %s/%s", secret.GetNamespace(), secret.GetName())
	_, err := vp.Clientset.Secrets(secret.GetNamespace()).Create(secret)
	if checkError(err) != nil {
		return err
	}
	return nil
}

func (vp *Operator) deleteUpstreamSecret(secret *v1.Secret) error {
	LogInfo("Deleted upstream secret %s/%s", secret.GetNamespace(), secret.GetName())
	err := vp.Clientset.Secrets(secret.GetNamespace()).Delete(
		secret.GetName(),
		&meta_v1.DeleteOptions{},
	)
	if checkError(err) != nil {
		return err
	}
	return nil
}

func (vp *Operator) updateUpstreamSecret(sCur, sOld *v1.Secret) error {
	if vp.isSecretNeedsUpdate(sCur, sOld) {
		LogInfo("Updated upstream secret %s/%s", sOld.GetNamespace(), sOld.GetName())
		_, err := vp.Clientset.Secrets(sOld.GetNamespace()).Update(sCur)
		if checkError(err) != nil {
			return err
		}
		return nil
	}
	LogInfo("Nothing changed. No need to update secret %s/%s", sOld.GetNamespace(), sOld.GetName())
	return nil
}

func (vp *Operator) checkCertificates() {
	for _, o := range vp.IngressInformer.GetStore().List() {
		i := o.(*v1beta1.Ingress)
		LogDebug("Added ingress %s/%s", i.GetNamespace(), i.GetName())
		vp.queue.Add(i)
	}
}
