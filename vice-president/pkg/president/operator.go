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
	// stores mapping of { host <string> : numAPIRequests <int>}
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

	vp := &Operator{
		Options:                    options,
		clientset:                  clientset,
		VicePresidentConfig:        vicePresidentConfig,
		viceClient:                 viceClient,
		RootCertPool:               rootCertPool,
		IntermediateCertificate:    intermediateCert,
		ResyncPeriod:               resyncPeriod,
		CertificateRecheckInterval: certificateRecheckInterval,
		rateLimitMap:               sync.Map{},
		ingressInformer:            newIngressInformer(clientset, resyncPeriod),
		secretInformer:             newSecretInformer(clientset, resyncPeriod),
		queue: workqueue.NewRateLimitingQueue(
			workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second),
		),
	}

	// add ingress event handlers
	vp.ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    vp.ingressAdd,
		UpdateFunc: vp.ingressUpdate,
	})

	// add secret event handlers
	vp.secretInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		DeleteFunc: vp.secretDelete,
	})

	return vp
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

	for i := 0; i < threadiness; i++ {
		go wait.Until(vp.runWorker, time.Second, stopCh)
	}

	LogInfo("Cache primed. Ready for operations.")

	ticker := time.NewTicker(vp.CertificateRecheckInterval)
	tickerResetRateLimit := time.NewTicker(RateLimitPeriod)
	go func() {
		for {
			select {
			case <-ticker.C:
				vp.checkCertificates()
				LogInfo("Next check in %v", vp.CertificateRecheckInterval)
			case <-tickerResetRateLimit.C:
				vp.resetRateLimits()
				LogInfo("Resetting all rate limits")
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
	} else if err != nil {
		LogError("%v failed with : %v", key, err)
	}

	// re-queue the key rate limited. will be processed later again.
	if vp.queue.NumRequeues(key) < 5 {
		vp.queue.AddRateLimited(key)
		return true
	}

	// max. retries in this reconciliation loop exceeded. forget for now.
	LogInfo("Ingress controller doesn't sync resources that often. Postponing adding ingress %v for %v", vp.VicePresidentConfig.ResyncPeriod)
	vp.queue.Forget(key)
	return true
}

func (vp *Operator) syncHandler(key string) error {
	o, exists, err := vp.ingressInformer.GetStore().GetByKey(key)
	if err != nil {
		utilruntime.HandleError(fmt.Errorf("%v failed with : %v", key, err))
		return err
	}
	if !exists {
		LogInfo("ingress %v was deleted", key)
		return nil
	}

	ingress := o.(*v1beta1.Ingress)
	// return right here if ingress is not annotated with vice-president: true
	if !isIngressHasAnnotation(ingress, AnnotationVicePresident) {
		LogDebug("Ignoring ingress %v/%v as vice-presidential annotation was not set.", ingress.GetNamespace(), ingress.GetName())
		return nil
	}
	// check each host
	for _, tls := range ingress.Spec.TLS {
		LogDebug("Checking ingress %v/%v: Hosts: %v, Secret: %v/%v", ingress.GetNamespace(), ingress.GetName(), tls.Hosts, ingress.GetNamespace(), tls.SecretName)

		if len(tls.Hosts) == 0 {
			return fmt.Errorf("no hosts found in ingress.spec.tls %v/%v", ingress.GetNamespace(), ingress.GetName())
		}
		// tls.Host[0] will be the CN, tls.Hosts[1:] the SANs of the certificate
		return vp.runStateMachine(ingress, tls.SecretName, tls.Hosts[0], tls.Hosts[1:])
	}
	return err
}

func (vp *Operator) runStateMachine(ingress *v1beta1.Ingress, secretName, host string, sans []string) error {
	// labels for prometheus metrics
	labels := prometheus.Labels{
		"ingress": fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName()),
		"host":    host,
		"sans":    strings.Join(sans, ","),
	}
	// add 0 to initialize the metrics that indicate failure
	initializeFailureMetrics(labels)

	tlsKeySecretKey, tlsCertSecretKey := ingressGetSecretKeysFromAnnotation(ingress)

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
				LogError("Couldn't enroll new certificate for ingress %s and host %s: %s", viceCert.GetIngressKey(), viceCert.Host, err)

				enrollFailedCounter.With(labels).Inc()

				return err
			}
			enrollSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateRenew:
			if err := vp.renewCertificate(viceCert); err != nil {
				LogError("Couldn't renew certificate for ingress %s, host %s using TID %s: %s.", viceCert.GetIngressKey(), viceCert.Host, viceCert.TID, err)

				renewFailedCounter.With(labels).Inc()

				return err
			}

			renewSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateApprove:
			if viceCert.Certificate != nil && viceCert.TID == "" {
				LogInfo("Certificate for ingress %s, host %s was automatically approved", viceCert.GetIngressKey(), viceCert.Host)
			} else {
				if err := vp.approveCertificate(viceCert); err != nil {
					LogError("Couldn't approve certificate for ingress %s, host %s using TID %s: %s", viceCert.GetIngressKey(), viceCert.Host, viceCert.TID, err)
					approveFailedCounter.With(labels).Inc()
					return err
				}
			}

			if err := vp.updateCertificateAndKeyInSecret(secret, viceCert, tlsKeySecretKey, tlsCertSecretKey); err != nil {
				approveFailedCounter.With(labels).Inc()
				return err
			}
			approveSuccessCounter.With(labels).Inc()

			nextState = IngressStateApproved

		case IngressStatePickup:
			if err := vp.pickupCertificate(viceCert); err != nil {
				LogError("Couldn't pickup certificate for ingress %s, host %s using TID %s: %s.", viceCert.GetIngressKey(), viceCert.Host, viceCert.TID, err)
				pickupFailedCounter.With(labels).Inc()
				return err
			}
			pickupSuccessCounter.With(labels).Inc()

			if err := vp.updateCertificateAndKeyInSecret(secret, viceCert, tlsKeySecretKey, tlsCertSecretKey); err != nil {
				return err
			}
			nextState = IngressStateApprove

		case IngressStateReplace:
			if err := vp.replaceCertificate(viceCert); err != nil {
				LogError("Couldn't replace certificate for ingress %s, host %s using TID %s: %s.", viceCert.GetIngressKey(), viceCert.Host, viceCert.TID, err)
				replaceFailedCounter.With(labels).Inc()
				return err
			}
			if err := vp.removeCertificateReplacementAnnotationIfLastHost(ingress, viceCert.Host); err != nil {
				LogError("could not remove annotation %s from ingress %s: %v", AnnotationCertificateReplacement, viceCert.GetIngressKey(), err)
				return err
			}
			replaceSuccessCounter.With(labels).Inc()

			nextState = IngressStateApprove

		case IngressStateApproved:
			return nil

		default:
			// check the secret. does it exist? does it contain a certificate and a key?
			// if not create empty secret in namespace of ingress and set to enrolling state
			v, s, err := vp.checkSecret(ingress, host, sans, secretName, tlsKeySecretKey, tlsCertSecretKey)
			if err != nil || v.Certificate == nil {
				if s == nil {
					// This is bad. Return an error here to allow requeueing the ingress after some time.
					return fmt.Errorf("couldn't get nor create secret %s/%s: %v", ingress.GetNamespace(), secretName, err)
				}
				nextState = IngressStateEnroll
			}
			viceCert = v
			secret = s

			if isIngressHasAnnotation(ingress, AnnotationCertificateReplacement) {
				nextState = IngressStateReplace
				continue
			}

			// if a certificate was found, validate it and act as necessary
			if viceCert.Certificate != nil {
				nextState = vp.checkViceCertificate(viceCert)
			}

		}
	}
	return nil
}

func (vp *Operator) removeCertificateReplacementAnnotationIfLastHost(ingress *v1beta1.Ingress, hostName string) error {
	// return if 'hostName' is not the last host in ingress.Spec.TLS
	if !isLastHostInIngressSpec(ingress, hostName) {
		LogDebug("Not removing annotation '%s=\"true\"' as %v is not the last host in ingress %s/%s", AnnotationCertificateReplacement, hostName, ingress.GetNamespace(), ingress.GetName())
		return nil
	}

	iObj, err := api.Scheme.Copy(ingress)
	if err != nil {
		return err
	}
	iCur := iObj.(*v1beta1.Ingress)
	annotations := iCur.GetAnnotations()
	delete(annotations, AnnotationCertificateReplacement)
	iCur.Annotations = annotations
	LogDebug("Removing annotation '%s=\"true\"' from ingress %s/%s", AnnotationCertificateReplacement, ingress.GetNamespace(), ingress.GetName())

	return vp.updateUpstreamIngress(ingress, iCur, isIngressAnnotationRemoved)
}

func (vp *Operator) checkSecret(ingress *v1beta1.Ingress, host string, sans []string, secretName, tlsKeySecretKey, tlsCertSecretKey string) (*ViceCertificate, *v1.Secret, error) {

	vc := NewViceCertificate(host, ingress.GetNamespace(), ingress.GetName(), sans, vp.IntermediateCertificate, vp.RootCertPool)
	secret, err := vp.clientset.Secrets(ingress.GetNamespace()).Get(secretName, meta_v1.GetOptions{})
	// does the secret exist?
	if err != nil {
		if apierrors.IsNotFound(err) {
			LogInfo("Secret %s/%s doesn't exist. Creating it and enrolling certificate", ingress.GetNamespace(), secretName)
			err = vp.addUpstreamSecret(
				newEmptySecret(ingress.GetNamespace(), secretName, ingress.GetLabels()),
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
	cert, key, err := getCertificateAndKeyFromSecret(secret, tlsKeySecretKey, tlsCertSecretKey)
	if err != nil {
		// do not return an error. get a new tls cert and key instead.
		LogError("Failed read from secret: %v", err)
		return vc, secret, nil
	}
	vc.Certificate = cert
	vc.PrivateKey = key

	return vc, secret, nil
}

// checkViceCertificate checks a given ViceCertificate and annotates the ingress accordingly
func (vp *Operator) checkViceCertificate(viceCert *ViceCertificate) string {
	// does the secret contain the correct key for the certificate?
	if !viceCert.DoesKeyAndCertificateTally() {
		LogInfo("Certificate and Key don't match")
		return IngressStateEnroll
	}

	//  is the certificate for the correct host?
	if !viceCert.DoesCertificateAndHostMatch() {
		LogInfo("Certificate and Host don't match")
		return IngressStateEnroll
	}

	// check remote by initiating TLS handshake
	if !viceCert.DoesRemoteCertificateMatch() {
		LogInfo("Mismatching remote certificate")
		return IngressStateEnroll
	}

	// is the certificate valid for time t ?
	if viceCert.DoesCertificateExpireSoon() {
		LogInfo("Certificate for host %s will expire in %s month. Renewing", viceCert.Host, vp.CertificateRecheckInterval)
		return IngressStateRenew
	}

	if viceCert.IsRevoked() {
		LogInfo("Certificate for host %s is revoked", viceCert.Host)
		return IngressStateReplace
	}

	LogInfo("Certificate for host %s is valid until %s", viceCert.Host, viceCert.Certificate.NotAfter.UTC())
	return IngressStateApproved
}

// updateCertificateInSecret adds or updates the certificate in a secret
func (vp *Operator) updateCertificateAndKeyInSecret(secret *v1.Secret, vc *ViceCertificate, tlsKeySecretKey, tlsCertSecretKey string) error {
	LogInfo("Add/Update certificate and key in secret %s/%s", secret.GetNamespace(), secret.GetName())
	updatedSecret, err := addCertificateAndKeyToSecret(vc, secret, tlsKeySecretKey, tlsCertSecretKey)
	if err != nil {
		LogError("Couldn't update secret %s/%s: %s", secret.Namespace, secret.Name, err)
		return err
	}
	return vp.updateUpstreamSecret(updatedSecret, secret)
}

// enrollCertificate triggers the enrollment of a certificate if rate limit is not exceeded
func (vp *Operator) enrollCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vc.enroll(vp.viceClient, vp.VicePresidentConfig); err != nil {
		LogError("Couldn't enroll certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// renewCertificate triggers the renewal of a certificate if rate limit is not exceeded
func (vp *Operator) renewCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vc.renew(vp.viceClient, vp.VicePresidentConfig); err != nil {
		LogError("Couldn't renew certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// approveCertificate triggers the approval of a certificate. no rate limit. always approve
func (vp *Operator) approveCertificate(vc *ViceCertificate) error {
	if err := vc.approve(vp.viceClient, vp.VicePresidentConfig); err != nil {
		LogError("Couldn't approve certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// pickupCertificate picks up a given certificate if rate limit is not exceeded
func (vp *Operator) pickupCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vc.pickup(vp.viceClient, vp.VicePresidentConfig); err != nil {
		LogError("Couldn't approve certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

// replaceCertificate triggers the replacement of the certificate if rate limit is not exceeded
func (vp *Operator) replaceCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vc.replace(vp.viceClient, vp.VicePresidentConfig); err != nil {
		LogError("Couldn't replace certificate for host %s: %s", vc.Host, err)
		return err
	}
	return nil
}

func (vp *Operator) ingressAdd(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		LogError("Couldn't add ingress %s/%s", i.GetNamespace(), i.GetName())
	}
	vp.queue.AddRateLimited(key)
}

func (vp *Operator) ingressUpdate(old, cur interface{}) {
	iOld := old.(*v1beta1.Ingress)
	iCur := cur.(*v1beta1.Ingress)

	if !isIngressNeedsUpdate(iCur, iOld) {
		LogDebug("Nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		return
	}

	key, err := cache.MetaNamespaceKeyFunc(cur)
	if err != nil {
		LogError("Couldn't add ingress %s/%s", iCur.GetNamespace(), iCur.GetName())
	}
	LogDebug("Ingress %s/%s was update", iOld.GetNamespace(), iOld.GetName())
	vp.queue.AddRateLimited(key)
	return
}

// watch secret and wait for max. t minutes until it exists or got modified
func (vp *Operator) waitForUpstreamSecret(secret *v1.Secret, watchConditionFunc watch.ConditionFunc) error {
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

	_, err = watch.Until(WaitTimeout, w, watchConditionFunc)
	return err
}

func (vp *Operator) addUpstreamSecret(secret *v1.Secret) error {
	s, err := vp.clientset.Secrets(secret.GetNamespace()).Create(secret)
	if err != nil {
		return err
	}
	LogDebug("Added upstream secret %s/%s", secret.GetNamespace(), secret.GetName())
	return vp.waitForUpstreamSecret(s, isSecretExists)
}

func (vp *Operator) deleteUpstreamSecret(secret *v1.Secret) error {
	err := vp.clientset.Secrets(secret.GetNamespace()).Delete(
		secret.GetName(),
		&meta_v1.DeleteOptions{},
	)
	if err != nil {
		return err
	}
	LogDebug("Deleted upstream secret %s/%s", secret.GetNamespace(), secret.GetName())
	return vp.waitForUpstreamSecret(secret, isSecretDeleted)
}

func (vp *Operator) updateUpstreamSecret(sCur, sOld *v1.Secret) error {
	if !isSecretNeedsUpdate(sCur, sOld) {
		LogDebug("Nothing changed. No need to update secret %s/%s", sOld.GetNamespace(), sOld.GetName())
		return nil
	}
	LogDebug("Updated upstream secret %s/%s", sOld.GetNamespace(), sOld.GetName())
	_, err := vp.clientset.Secrets(sOld.GetNamespace()).Update(sCur)
	return err
}

func (vp *Operator) updateUpstreamIngress(iOld, iCur *v1beta1.Ingress, conditionFunc watch.ConditionFunc) error {
	if reflect.DeepEqual(iOld.Spec, iCur.Spec) && reflect.DeepEqual(iOld.GetAnnotations(), iCur.GetAnnotations()) {
		LogDebug("Nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		return nil
	}
	ing, err := vp.clientset.ExtensionsV1beta1().Ingresses(iOld.GetNamespace()).Update(iCur)
	if err != nil {
		return err
	}

	LogInfo("Updated upstream ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
	return vp.waitForUpstreamIngress(ing, conditionFunc)
}

func (vp *Operator) waitForUpstreamIngress(ingress *v1beta1.Ingress, conditionFunc watch.ConditionFunc) error {
	w, err := vp.clientset.ExtensionsV1beta1().Ingresses(ingress.GetNamespace()).Watch(
		meta_v1.SingleObject(
			meta_v1.ObjectMeta{
				Name: ingress.GetName(),
			},
		),
	)
	if err != nil {
		return err
	}

	_, err = watch.Until(WaitTimeout, w, conditionFunc)
	return err
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

func (vp *Operator) secretDelete(obj interface{}) {
	secret := obj.(*v1.Secret)
	if ingress := vp.secretReferencedByIngress(secret); ingress != nil {
		LogDebug("Secret %s/%s, referenced by ingress %s/%s, was deleted. Requeueing ingress if not already queued.", secret.GetNamespace(), secret.GetName(), ingress.GetNamespace(), ingress.GetName())
		key, err := cache.MetaNamespaceKeyFunc(ingress)
		if err != nil {
			LogError("Couldn't create key for ingress %s/%s: %v", ingress.GetNamespace(), ingress.GetName(), err)
		}
		vp.queue.AddAfter(key, BaseDelay)
	}
}

func (vp *Operator) secretReferencedByIngress(secret *v1.Secret) *v1beta1.Ingress {
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

func (vp *Operator) resetRateLimits() {
	vp.rateLimitMap = sync.Map{}
	apiRateLimitHitGauge.Reset()
}

func (vp *Operator) isRateLimitForHostExceeded(viceCert *ViceCertificate) bool {
	if vp.VicePresidentConfig.RateLimit == -1 {
		return false
	}
	if n, ok := vp.rateLimitMap.LoadOrStore(viceCert.Host, 1); ok {
		numRequests := n.(int)
		if numRequests >= vp.VicePresidentConfig.RateLimit {
			LogInfo("Limit of %v request(s)/%v for host %s reached. Skipping further requests", vp.VicePresidentConfig.RateLimit, RateLimitPeriod, viceCert.Host)
			apiRateLimitHitGauge.With(prometheus.Labels{
				"ingress": viceCert.GetIngressKey(),
				"host":    viceCert.Host,
				"sans":    viceCert.GetSANsString(),
			}).Set(1.0)
			return true
		}
		vp.rateLimitMap.Store(viceCert.Host, numRequests+1)
	}
	return false
}
