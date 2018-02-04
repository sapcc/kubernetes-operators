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
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/go-vice"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
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
)

// Operator is the vice-president certificate operator
type Operator struct {
	Options

	VicePresidentConfig VicePresidentConfig

	clientset       *kubernetes.Clientset
	viceClient      *vice.Client
	ingressInformer cache.SharedIndexInformer
	secretInformer  cache.SharedIndexInformer

	RootCertPool            *x509.CertPool
	IntermediateCertificate *x509.Certificate

	// ResyncPeriod defines the period after which the local cache of ingresses is refreshed
	ResyncPeriod time.Duration
	// CertificateRecheckInterval defines the period after which certificates are checked
	CertificateRecheckInterval time.Duration

	queue workqueue.RateLimitingInterface

	// stores mapping of { host string : numAPIRequests int}
	rateLimitMap sync.Map
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

	resyncPeriod := time.Duration(vicePresidentConfig.ResyncPeriod) * time.Minute
	certificateRecheckInterval := time.Duration(vicePresidentConfig.CertificateCheckInterval) * time.Minute

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		LogFatal("Couldn't create Kubernetes client: %s", err)
	}

	cert, err := tls.LoadX509KeyPair(options.ViceCrtFile, options.ViceKeyFile)
	if err != nil {
		LogFatal("Couldn't load certificate from %s and/or key from %s for vice client %s", options.ViceCrtFile, options.ViceKeyFile, err)
	}
	// create a new vice client or die
	viceClient := vice.New(cert)
	if viceClient == nil {
		LogFatal("Couldn't create vice client: %s", err)
	}

	intermediateCert, err := readCertFromFile(options.IntermediateCertificate)
	if err != nil {
		LogFatal("Couldn't read intermediate certificate %s", err)
	}

	caCert, err := readCertFromFile(options.ViceCrtFile)
	if err != nil {
		LogFatal("Couldn't read CA Cert. Aborting.")
	}
	rootCertPool := x509.NewCertPool()
	rootCertPool.AddCert(caCert)

	operator := &Operator{
		Options:                    options,
		clientset:                  clientset,
		VicePresidentConfig:        vicePresidentConfig,
		viceClient:                 viceClient,
		RootCertPool:               rootCertPool,
		IntermediateCertificate:    intermediateCert,
		ResyncPeriod:               resyncPeriod,
		CertificateRecheckInterval: certificateRecheckInterval,
		rateLimitMap:               sync.Map{},
		queue:                      workqueue.NewRateLimitingQueue(workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second)),
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
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	IngressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.ingressAdd,
		UpdateFunc: operator.ingressUpdate,
	})

	operator.ingressInformer = IngressInformer

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
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	SecretInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		UpdateFunc: operator.secretUpdate,
		DeleteFunc: operator.secretDelete,
	})

	operator.secretInformer = SecretInformer

	return operator
}

// Run starts the operator
func (vp *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer utilruntime.HandleCrash()
	defer vp.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)

	LogInfo("Ladies and Gentlemen, the Vice President! Renewing your Symantec certificates now in version %v\n", VERSION)

	go vp.ingressInformer.Run(stopCh)
	go vp.secretInformer.Run(stopCh)

	LogInfo("Waiting for cache to sync...")
	cache.WaitForCacheSync(
		stopCh,
		vp.ingressInformer.HasSynced,
		vp.secretInformer.HasSynced,
	)
	LogInfo("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(vp.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(vp.CertificateRecheckInterval)
	tickerResetRateLimit := time.NewTicker(1 * time.Hour)
	go func() {
		for {
			select {
			case <-ticker.C:
				vp.checkCertificates()
				LogInfo("Next check in %v", vp.CertificateRecheckInterval)
			case <-tickerResetRateLimit.C:
				vp.resetRateLimit()
				LogInfo("Resetting rate limits")
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
	err := vp.syncHandler(key.(string))
	if err == nil {
		vp.queue.Forget(key)
		return true
	}

	LogError("%v failed with : %v", key, err)
	vp.queue.AddAfter(key, vp.CertificateRecheckInterval)

	return true
}

func (vp *Operator) syncHandler(key string) error {
	o, exists, err := vp.ingressInformer.GetStore().GetByKey(key)
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

			LogDebug("Checking ingress %v/%v: Hosts: %v, Secret: %v/%v", ingress.GetNamespace(), ingress.GetName(), tls.Hosts, ingress.GetNamespace(), tls.SecretName)

			if len(tls.Hosts) == 0 {
				return fmt.Errorf("No hosts found in ingress %v/%v", ingress.GetNamespace(), ingress.GetName())
			}
			return vp.runStateMachine(ingress, tls.SecretName, tls.Hosts[0], tls.Hosts[1:])
		}
	} else {
		LogDebug("Ignoring ingress %v/%v as vice-presidential annotation was not set.", ingress.GetNamespace(), ingress.GetName())
	}
	return err
}

func (vp *Operator) runStateMachine(ingress *v1beta1.Ingress, secretName, host string, sans []string) error {
	ingressKey := fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName())
	// labels for prometheus metrics
	labels := prometheus.Labels{
		"ingress": ingressKey,
		"host":    host,
		"sans":    strings.Join(sans, ","),
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
				LogInfo("Couldn't enroll new certificate for ingress %s and host %s: %s", ingressKey, viceCert.Host, err)

				enrollFailedCounter.With(labels).Inc()

				return err
			}
			enrollSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateRenew:
			if err := vp.renewCertificate(viceCert); err != nil {
				LogInfo("Couldn't renew certificate for ingress %s, host %s using TID %s: %s.", ingressKey, viceCert.Host, viceCert.TID, err)

				renewFailedCounter.With(labels).Inc()

				return err
			}

			renewSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateApprove:
			if viceCert.Certificate != nil && viceCert.TID == "" {
				LogInfo("Certificate for ingress %s, host %s was automatically approved", ingressKey, viceCert.Host)
			} else {
				if err := vp.approveCertificate(viceCert); err != nil {
					LogInfo("Couldn't approve certificate for ingress %s, host %s using TID %s: %s", ingressKey, viceCert.Host, viceCert.TID, err)
					approveFailedCounter.With(labels).Inc()
					return err
				}
			}

			if err := vp.updateCertificateAndKeyInSecret(secret, viceCert); err != nil {
				approveFailedCounter.With(labels).Inc()
				return err
			}

			approveSuccessCounter.With(labels).Inc()

			nextState = IngressStateApproved

		case IngressStatePickup:
			if err := vp.pickupCertificate(viceCert); err != nil {
				LogInfo("Couldn't pickup certificate for ingress %s, host %s using TID %s: %s.", ingressKey, viceCert.Host, viceCert.TID, err)

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
			v, s, err := vp.checkSecret(ingress, host, sans, secretName)
			if err != nil || v.Certificate == nil {
				if s == nil {
					// This is bad. Return an error here to allow requeueing the ingress after some time.
					return fmt.Errorf("Couldn't get nor create secret %s/%s: %v", ingress.GetNamespace(), secretName, err)
				}
				nextState = IngressStateEnroll
			}
			viceCert = v
			secret = s

			// if a certificate was found, validate it
			if viceCert.Certificate != nil {
				nextState = vp.checkViceCertificate(viceCert, ingressKey)
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

func (vp *Operator) checkSecret(ingress *v1beta1.Ingress, host string, sans []string, secretName string) (*ViceCertificate, *v1.Secret, error) {

	vc := &ViceCertificate{Host: host, IntermediateCertificate: vp.IntermediateCertificate, Roots: vp.RootCertPool}
	vc.SetSANs(sans)

	secret, err := vp.clientset.Secrets(ingress.GetNamespace()).Get(secretName, meta_v1.GetOptions{})

	// does the secret exist?
	if err != nil {
		if apierrors.IsNotFound(err) {
			LogInfo("Secret %s/%s doesn't exist. Creating it and enrolling certificate", ingress.GetNamespace(), secretName)
			err = vp.addUpstreamSecret(
				vp.createEmptySecret(ingress.GetNamespace(), secretName, ingress.GetLabels()),
			)
			if err != nil {
				return nil, nil, fmt.Errorf("couldn't create secret %s/%s: %v", ingress.GetNamespace(), secretName, err)
			}
			// try to get secret again
			secret, err := vp.clientset.Secrets(ingress.GetNamespace()).Get(secretName, meta_v1.GetOptions{})
			if err != nil {
				return nil, nil, err
			}
			return vc, secret, nil
		}
		LogError("Couldn't get secret %s/%s: %v", ingress.GetNamespace(), secretName, err)
		return nil, nil, err
	}

	// does the certificate exist? can it be decoded and parsed from the secret?
	cert, key, err := vp.getCertificateAndKeyFromSecret(secret)
	if err != nil {
		// do not return an error. get a new tls cert and key instead.
		LogError(err.Error())
		return vc, secret, nil
	}
	vc.Certificate = cert
	vc.PrivateKey = key

	return vc, secret, nil
}

// checkViceCertificate checks a given ViceCertificate and sets the state accordingly
func (vp *Operator) checkViceCertificate(viceCert *ViceCertificate, ingressKey string) string {
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

	// check remote by initiating TLS handshake
	if !viceCert.DoesRemoteCertificateMatch() {
		LogInfo("Mismatching remote certificate. Enrolling new one")
		return IngressStateEnroll
	}

	// is the certificate valid for time t ?
	if viceCert.DoesCertificateExpireSoon() {
		LogInfo("Certificate for host %s will expire in %s month. Renewing", viceCert.Host, vp.CertificateRecheckInterval)
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

func (vp *Operator) resetRateLimit() {
	vp.rateLimitMap = sync.Map{}
	apiRateLimitHitGauge.Reset()
}

func (vp *Operator) checkRateLimitForHostExceeded(viceCert *ViceCertificate) bool {
	if n, ok := vp.rateLimitMap.LoadOrStore(viceCert.Host, 1); ok {
		numRequests := n.(int)
		if numRequests >= vp.VicePresidentConfig.RateLimit {
			LogInfo("Limit of %v requests/hour for host %s reached. Skipping", vp.VicePresidentConfig.RateLimit, viceCert.Host)
			apiRateLimitHitGauge.With(prometheus.Labels{
				"ingress": viceCert.GetIngressKey(),
				"host":    viceCert.Host,
				"sans":    viceCert.GetSANsString(),
			}).Inc()
			return true
		}
		vp.rateLimitMap.Store(viceCert.Host, numRequests+1)
	}
	return false
}

// EnrollCertificate triggers the enrollment of a certificate if the rate limit is not exceeded
func (vp *Operator) enrollCertificate(vc *ViceCertificate) error {
	if !vp.checkRateLimitForHostExceeded(vc) {
		if err := vc.enroll(vp); err != nil {
			LogError(err.Error())
			return err
		}
	}
	return nil
}

// RenewCertificate triggers the renewal of a certificate if the rate limit is not exceeded
func (vp *Operator) renewCertificate(vc *ViceCertificate) error {
	if vp.checkRateLimitForHostExceeded(vc) {
		if err := vc.renew(vp); err != nil {
			LogError(err.Error())
			return err
		}
	}
	return nil
}

// ApproveCertificate triggers the approval of a certificate
func (vp *Operator) approveCertificate(vc *ViceCertificate) error {
	if err := vc.approve(vp); err != nil {
		LogError(err.Error())
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

func (vp *Operator) createEmptySecret(nameSpace, secretName string, labels map[string]string) *v1.Secret {
	if labels == nil {
		labels = map[string]string{}
	}
	return &v1.Secret{
		ObjectMeta: meta_v1.ObjectMeta{
			Name:      secretName,
			Namespace: nameSpace,
			Labels:    labels,
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

	certPEM, err := writeCertificatesToPEM(viceCert.WithIntermediateCertificate())
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

	secret.Data[SecretTLSCertType] = removeSpecialCharactersFromPEM(certPEM)
	secret.Data[SecretTLSKeyType] = removeSpecialCharactersFromPEM(keyPEM)

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
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		LogError("Couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
	}
	// need to add with some delay to avoid errors when ingress is added and secret is deleted at the same time
	vp.queue.AddAfter(key, BaseDelay)
}

func (vp *Operator) ingressUpdate(cur, old interface{}) {
	iOld := old.(*v1beta1.Ingress)
	iCur := cur.(*v1beta1.Ingress)

	if vp.isIngressNeedsUpdate(iCur, iOld) {
		LogDebug("Updated ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		key, err := cache.MetaNamespaceKeyFunc(cur)
		if err != nil {
			LogError("Couldn't add ingress %s/%s", iCur.GetNamespace(), iCur.GetName())
		}
		// need to add with some delay to avoid errors when ingress is added and secret is deleted at the same time
		vp.queue.AddAfter(key, BaseDelay)
		return
	}
	LogDebug("Nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
}

// watch secret and wait for max. t minutes until it exists or got modified
func (vp *Operator) waitForUpstreamSecret(secret *v1.Secret) error {
	w, err := vp.clientset.Secrets(secret.GetNamespace()).Watch(
		meta_v1.SingleObject(
			meta_v1.ObjectMeta{
				Name: secret.GetName(),
			},
		),
	)
	if err != nil {
		return err
	}

	_, err = watch.Until(1*time.Minute, w, secretExists)
	if err != nil {
		return err
	}

	return nil
}

func secretExists(event watch.Event) (bool, error) {
	switch event.Type {
	case watch.Deleted:
		return false, apierrors.NewNotFound(schema.GroupResource{Resource: "secret"}, "")
	case watch.Added, watch.Modified:
		return true, nil
	}
	return false, nil
}

func (vp *Operator) addUpstreamSecret(secret *v1.Secret) error {
	LogDebug("Added upstream secret %s/%s", secret.GetNamespace(), secret.GetName())
	s, err := vp.clientset.Secrets(secret.GetNamespace()).Create(secret)
	if checkError(err) != nil {
		return err
	}
	err = vp.waitForUpstreamSecret(s)
	if err != nil {
		return err
	}
	return nil
}

func (vp *Operator) deleteUpstreamSecret(secret *v1.Secret) error {
	LogDebug("Deleted upstream secret %s/%s", secret.GetNamespace(), secret.GetName())
	err := vp.clientset.Secrets(secret.GetNamespace()).Delete(
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
		LogDebug("Updated upstream secret %s/%s", sOld.GetNamespace(), sOld.GetName())
		s, err := vp.clientset.Secrets(sOld.GetNamespace()).Update(sCur)
		if checkError(err) != nil {
			return err
		}
		err = vp.waitForUpstreamSecret(s)
		if err != nil {
			return err
		}
		return nil
	}
	LogDebug("Nothing changed. No need to update secret %s/%s", sOld.GetNamespace(), sOld.GetName())
	return nil
}

func (vp *Operator) checkCertificates() {
	for _, o := range vp.ingressInformer.GetStore().List() {
		i := o.(*v1beta1.Ingress)
		key, err := cache.MetaNamespaceKeyFunc(o)
		if err != nil {
			LogError("Couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
		}
		LogDebug("Added ingress %s/%s", i.GetNamespace(), i.GetName())
		vp.queue.Add(key)
	}
}

func (vp *Operator) secretUpdate(cur, old interface{}) {
	sCur := cur.(*v1.Secret)
	sOld := old.(*v1.Secret)
	if vp.isSecretNeedsUpdate(sCur, sOld) {
		if ingress := vp.isSecretReferencedByIngress(sCur); ingress != nil {
			LogDebug("Secret %s/%s, referenced by ingress %s/%s, was updated. Requeueing ingress if not already queued.", sCur.GetNamespace(), sCur.GetName(), ingress.GetNamespace(), ingress.GetName())
			key, err := cache.MetaNamespaceKeyFunc(ingress)
			if err != nil {
				LogError("Couldn't create key for ingress %s/%s: %v", ingress.GetNamespace(), ingress.GetName(), err)
			}
			vp.queue.AddAfter(key, BaseDelay)
		}
	}
}

func (vp *Operator) secretDelete(obj interface{}) {
	secret := obj.(*v1.Secret)
	if ingress := vp.isSecretReferencedByIngress(secret); ingress != nil {
		LogDebug("Secret %s/%s, referenced by ingress %s/%s, was deleted. Requeueing ingress if not already queued.", secret.GetNamespace(), secret.GetName(), ingress.GetNamespace(), ingress.GetName())
		key, err := cache.MetaNamespaceKeyFunc(ingress)
		if err != nil {
			LogError("Couldn't create key for ingress %s/%s: %v", ingress.GetNamespace(), ingress.GetName(), err)
		}
		vp.queue.AddAfter(key, BaseDelay)
	}
}

func (vp *Operator) isSecretReferencedByIngress(secret *v1.Secret) *v1beta1.Ingress {
	for _, iObj := range vp.ingressInformer.GetStore().List() {
		ingress := iObj.(*v1beta1.Ingress)
		if secret.GetNamespace() == ingress.GetNamespace() {
			for _, tls := range ingress.Spec.TLS {
				if secret.GetName() == tls.SecretName {
					return ingress
				}
			}
		}
	}
	return nil
}
