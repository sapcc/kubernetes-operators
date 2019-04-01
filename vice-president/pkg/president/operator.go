/*******************************************************************************
*
* Copyright 2019 SAP SE
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

	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	v12 "k8s.io/client-go/kubernetes/typed/core/v1"
	"k8s.io/client-go/pkg/api"
	v1 "k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/pkg/apis/extensions/v1beta1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/util/workqueue"
)

var (
	// VERSION of the vice president
	VERSION = "0.0.0.dev"
)

// Operator is the vice-president certificate operator
type Operator struct {
	Options

	vicePresidentConfig      VicePresidentConfig
	rootCertPool             *x509.CertPool
	intermediateCertificate  *x509.Certificate
	resyncInterval           time.Duration // ResyncInterval defines the period after which the local cache of ingresses is refreshed
	certificateCheckInterval time.Duration // CertificateCheckInterval defines the period after which certificates are checked
	clientset                *kubernetes.Clientset
	viceClient               *viceClient
	ingressInformer          cache.SharedIndexInformer
	secretInformer           cache.SharedIndexInformer
	queue                    workqueue.RateLimitingInterface
	rateLimitMap             sync.Map // stores mapping of { host <string> : numAPIRequests <int>}
	logger                   log.Logger
	eventRecorder            record.EventRecorder
}

// New creates a new operator using the given options
func New(options Options, logger log.Logger) *Operator {
	viceLogger := log.NewLoggerWith(logger, "component", "viceClient")
	logger = log.NewLoggerWith(logger, "component", "operator")
	logger.LogDebug("creating new vice president", "version", VERSION)

	if err := options.CheckOptions(); err != nil {
		logger.LogFatal("error in configuration", "err", err)
	}

	vicePresidentConfig, err := ReadConfig(options.VicePresidentConfig)
	if err != nil {
		logger.LogFatal("could get vice configuration", "err", err)
	}

	config, err := newClientConfig(options)
	if err != nil {
		logger.LogFatal("couldn't get kubernetes client config", "err", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		logger.LogFatal("Couldn't create Kubernetes client", "err", err)
	}

	cert, err := tls.LoadX509KeyPair(options.ViceCrtFile, options.ViceKeyFile)
	if err != nil {
		logger.LogFatal("couldn't load certificate for vice client", "cert", options.ViceCrtFile, "key", options.ViceKeyFile, "err", err)
	}

	// create a new vice client or die
	viceClient := newViceClient(cert, vicePresidentConfig, viceLogger)
	if viceClient == nil {
		logger.LogFatal("couldn't create vice client", "err", err)
	}

	intermediateCert, err := readCertFromFile(options.IntermediateCertificate)
	if err != nil {
		logger.LogFatal("couldn't read intermediate certificate", "err", err)
	}

	caCert, err := readCertFromFile(options.ViceCrtFile)
	if err != nil {
		logger.LogFatal("couldn't read CA Cert", "err", err)
	}
	rootCertPool := x509.NewCertPool()
	rootCertPool.AddCert(caCert)

	b := record.NewBroadcaster()
	b.StartLogging(logger.LogEvent)
	b.StartRecordingToSink(&v12.EventSinkImpl{
		Interface: clientset.CoreV1().Events(""),
	})
	eventRecorder := b.NewRecorder(scheme.Scheme, v1.EventSource{
		Component: EventComponent,
	})

	vp := &Operator{
		logger:                   logger,
		Options:                  options,
		clientset:                clientset,
		vicePresidentConfig:      vicePresidentConfig,
		viceClient:               viceClient,
		rootCertPool:             rootCertPool,
		intermediateCertificate:  intermediateCert,
		resyncInterval:           options.ResyncInterval,
		certificateCheckInterval: options.CertificateCheckInterval,
		rateLimitMap:             sync.Map{},
		ingressInformer:          newIngressInformer(clientset, options.ResyncInterval),
		secretInformer:           newSecretInformer(clientset, options.ResyncInterval),
		eventRecorder:            eventRecorder,
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

	vp.logger.LogInfo("Ladies and Gentlemen, the Vice President! Renewing your Symantec certificates.", "version", VERSION)

	go vp.ingressInformer.Run(stopCh)
	go vp.secretInformer.Run(stopCh)

	vp.logger.LogInfo("waiting for cache to sync...")
	cache.WaitForCacheSync(
		stopCh,
		vp.ingressInformer.HasSynced,
		vp.secretInformer.HasSynced,
	)

	for i := 0; i < threadiness; i++ {
		go wait.Until(vp.runWorker, time.Second, stopCh)
	}

	vp.logger.LogInfo("cache primed. ready for operations.")

	ticker := time.NewTicker(vp.certificateCheckInterval)
	tickerResetRateLimit := time.NewTicker(RateLimitPeriod)
	go func() {
		for {
			select {
			case <-ticker.C:
				vp.checkCertificates()
				vp.logger.LogInfo("next check", "interval", vp.certificateCheckInterval)
			case <-tickerResetRateLimit.C:
				vp.resetRateLimits()
				vp.logger.LogInfo("resetting all rate limits")
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
		vp.logger.LogError("error handling ingress", err, "key", key)
	}

	// re-queue the key rate limited. will be processed later again.
	if vp.queue.NumRequeues(key) < 5 {
		vp.queue.AddRateLimited(key)
		return true
	}

	// max. retries in this reconciliation loop exceeded. forget for now.
	vp.logger.LogInfo("max retries reached. trying again in next reconciliation loop.", "key", key, "waiting", vp.ResyncInterval)
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
		vp.logger.LogInfo("ingress was deleted", "key", key)
		return nil
	}

	ingress := o.(*v1beta1.Ingress)
	// return right here if ingress is not annotated with vice-president: true
	if !isIngressHasAnnotation(ingress, AnnotationVicePresident) {
		vp.logger.LogDebug("ignoring ingress as vice-presidential annotation is not set", "key", key)
		return nil
	}
	// check each host
	for _, tls := range ingress.Spec.TLS {
		vp.logger.LogDebug("checking ingress", "key", key, "hosts", strings.Join(tls.Hosts, ", "), "secret", secretKey(ingress.GetNamespace(), tls.SecretName))
		if len(tls.Hosts) == 0 {
			return fmt.Errorf("no hosts found in ingress.spec.tls. key %s", key)
		}

		// tls.Host[0] will be the CN, tls.Hosts[1:] the SANs of the certificate.
		vc := NewViceCertificate(ingress, tls.SecretName, tls.Hosts[0], tls.Hosts[1:], vp.intermediateCertificate, vp.rootCertPool)
		return vp.checkCertificate(vc)
	}
	return err
}

func (vp *Operator) checkCertificate(vc *ViceCertificate) error {
	// Labels to be used for prometheus metrics.
	labels := prometheus.Labels{
		"ingress": vc.getIngressKey(),
		"host":    vc.host,
		"sans":    vc.getSANsString(),
	}

	// Check if an alternative key for the TLS certificate and private key is configured via annotation on the ingress.
	tlsKeySecretKey, tlsCertSecretKey := ingressGetSecretKeysFromAnnotation(vc.ingress)

	var state, nextState string

	// Find the secret or create it.
	// Find the TLS certificate and key or create them (IngressStateEnroll).
	// Check the TLS certificate and key or re-create (IngressStateEnroll|IngressStateReplace) or renew (IngressStateRenew) them.
	// If a certificate was enrolled, renewed or replaced and approval is required using the the certificates transaction id (TID).
	// Add/update the approved certificate to the referenced secret.
	for {
		state = nextState
		switch state {
		case IngressStateEnroll:
			if err := vp.enrollCertificate(vc); err != nil {
				vp.logger.LogError("couldn't enroll certificate", err, "key", vc.getIngressKey(), "host", vc.host)
				enrollFailedCounter.With(labels).Inc()
				return err
			}
			enrollSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStateRenew:
			if err := vp.renewCertificate(vc); err != nil {
				vp.logger.LogError("couldn't renew certificate", err, "key", vc.getIngressKey(), "host", vc.host, "tid", vc.tid)
				renewFailedCounter.With(labels).Inc()
				return err
			}
			renewSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStatePickup:
			if err := vp.pickupCertificate(vc); err != nil {
				vp.logger.LogError("couldn't pickup certificate", err, "key", vc.getIngressKey(), "host", vc.host, "tid", vc.tid)
				pickupFailedCounter.With(labels).Inc()
				return err
			}
			if err := vp.updateCertificateAndKeyInSecret(vc, tlsKeySecretKey, tlsCertSecretKey); err != nil {
				return err
			}
			pickupSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStateReplace:
			if err := vp.replaceCertificate(vc); err != nil {
				vp.logger.LogError("couldn't replace certificate", err, "key", vc.getIngressKey(), "host", vc.host, "tid", vc.tid)
				replaceFailedCounter.With(labels).Inc()
				return err
			}
			if err := vp.removeCertificateReplacementAnnotationIfLastHost(vc); err != nil {
				vp.logger.LogError("couldn't remove annotation", err, "key", vc.getIngressKey(), "annotation", AnnotationCertificateReplacement)
				return err
			}
			replaceSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStateApprove:
			if vc.certificate != nil && vc.tid == "" {
				vp.logger.LogInfo("certificate was automatically approved", "key", vc.getIngressKey(), "host", vc.host)
			} else {
				if err := vp.approveCertificate(vc); err != nil {
					vp.logger.LogError("couldn't approve certificate", err, "ingress", vc.getIngressKey(), "host", vc.host, "tid", vc.tid)
					approveFailedCounter.With(labels).Inc()
					return err
				}
			}
			if err := vp.updateCertificateAndKeyInSecret(vc, tlsKeySecretKey, tlsCertSecretKey); err != nil {
				approveFailedCounter.With(labels).Inc()
				return err
			}
			approveSuccessCounter.With(labels).Inc()
			vp.eventRecorder.Eventf(vc.ingress, v1.EventTypeNormal, UpdateEvent, fmt.Sprintf("updated certificate for host %s, ingress %s", vc.host, vc.getIngressKey()))
			nextState = IngressStateApproved

		case IngressStateApproved:
			// Certificate approved. We're done.
			return nil

		default:
			secret, err := vp.getOrCreateSecret(vc)
			if err != nil {
				return errors.Wrapf(err, "couldn't get nor create secret %s", vc.getSecretKey())
			}

			tlsCert, tlsKey, err := getCertificateAndKeyFromSecret(secret, tlsKeySecretKey, tlsCertSecretKey)
			if err != nil {
				vp.logger.LogInfo("no certificate and/or key found in secret %s", vc.getSecretKey())
				nextState = IngressStateEnroll
			}
			vc.certificate = tlsCert
			vc.privateKey = tlsKey

			if isIngressHasAnnotation(vc.ingress, AnnotationCertificateReplacement) {
				nextState = IngressStateReplace
				continue
			}

			nextState = vp.getNextState(vc)
		}
	}
	return nil
}

func (vp *Operator) getNextState(vc *ViceCertificate) string {
	if !vc.DoesKeyAndCertificateTally() {
		vp.logger.LogInfo("certificate and key don't match", "host", vc.host)
		return IngressStateEnroll
	}

	//  is the certificate for the correct host?
	if !vc.DoesCertificateAndHostMatch() {
		vp.logger.LogInfo("certificate and host don't match", "host", vc.host)
		return IngressStateEnroll
	}

	if vp.EnableValidateRemoteCertificate {
		if !vc.DoesRemoteCertificateMatch() {
			vp.logger.LogInfo("mismatching remote certificate", "host", vc.host)
			return IngressStateEnroll
		}
	}

	if vc.DoesCertificateExpireSoon(vp.MinCertValidityDays) {
		return IngressStateRenew
	}

	if vc.IsRevoked() {
		return IngressStateReplace
	}

	vp.logger.LogInfo("certificate ist valid", "host", vc.host, "validUntil", vc.certificate.NotAfter.UTC().String())
	return IngressStateApproved
}

func (vp *Operator) getOrCreateSecret(vc *ViceCertificate) (*v1.Secret, error) {
	secret, err := vp.clientset.Secrets(vc.ingress.GetNamespace()).Get(vc.secretName, meta_v1.GetOptions{})
	if err != nil {
		// Create secret if not found.
		if apierrors.IsNotFound(err) {
			vp.logger.LogInfo("creating secret", "key", vc.getSecretKey())
			if err := vp.addUpstreamSecret(newEmptySecret(vc.ingress.GetNamespace(), vc.secretName, vc.ingress.GetLabels())); err != nil {
				return nil, errors.Wrapf(err, "couldn't create secret %s", vc.getSecretKey())
			}
			return vp.clientset.Secrets(vc.ingress.GetNamespace()).Get(vc.secretName, meta_v1.GetOptions{})
		}
		// Return any other error.
		return nil, errors.Wrapf(err, "couldn't get secret %s", vc.getSecretKey())
	}
	return secret, nil
}

func (vp *Operator) removeCertificateReplacementAnnotationIfLastHost(vc *ViceCertificate) error {
	ingress, err := vp.clientset.Ingresses(vc.ingress.GetNamespace()).Get(vc.ingress.GetName(), meta_v1.GetOptions{})
	if err != nil {
		return err
	}

	// return if 'hostName' is not the last host in ingress.Spec.TLS
	if !isLastHostInIngressSpec(ingress, vc.host) {
		vp.logger.LogDebug(
			"not removing annotation as it's not the last host",
			"key", vc.getIngressKey(),
			"host", AnnotationCertificateReplacement,
			"host", vc.host,
		)
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

	vp.logger.LogDebug("removing annotation", "key", vc.getIngressKey(), "annotation", AnnotationCertificateReplacement)
	return vp.updateUpstreamIngress(ingress, iCur, isIngressAnnotationRemoved)
}

// updateCertificateInSecret adds or updates the certificate in a secret
func (vp *Operator) updateCertificateAndKeyInSecret(vc *ViceCertificate, tlsKeySecretKey, tlsCertSecretKey string) error {
	secret, err := vp.clientset.Secrets(vc.ingress.GetNamespace()).Get(vc.secretName, meta_v1.GetOptions{})
	if err != nil {
		return err
	}
	vp.logger.LogInfo("add/update certificate to secret", "key", vc.getSecretKey())
	updatedSecret, err := addCertificateAndKeyToSecret(vc, secret, tlsKeySecretKey, tlsCertSecretKey)
	if err != nil {
		vp.logger.LogError("couldn't update secret", err, "key", vc.getSecretKey())
		return err
	}
	return vp.updateUpstreamSecret(updatedSecret, secret)
}

// enrollCertificate triggers the enrollment of a certificate if rate limit is not exceeded
func (vp *Operator) enrollCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}

	if err := vp.viceClient.enroll(vc); err != nil {
		vp.logger.LogError("couldn't enroll certificate", err, "host", vc.host)
		return err
	}
	return nil
}

// renewCertificate triggers the renewal of a certificate if rate limit is not exceeded
func (vp *Operator) renewCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vp.viceClient.renew(vc); err != nil {
		vp.logger.LogError("couldn't renew certificate", err, "host", vc.host)
		return err
	}
	return nil
}

// approveCertificate triggers the approval of a certificate. no rate limit. always approve
func (vp *Operator) approveCertificate(vc *ViceCertificate) error {
	if err := vp.viceClient.approve(vc); err != nil {
		vp.logger.LogError("couldn't approve certificate", err, "host", vc.host)
		return err
	}
	return nil
}

// pickupCertificate picks up a given certificate if rate limit is not exceeded
func (vp *Operator) pickupCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vp.viceClient.pickup(vc); err != nil {
		vp.logger.LogError("couldn't approve certificate", err, "host", vc.host)
		return err
	}
	return nil
}

// replaceCertificate triggers the replacement of the certificate if rate limit is not exceeded
func (vp *Operator) replaceCertificate(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	if err := vp.viceClient.replace(vc); err != nil {
		vp.logger.LogError("couldn't replace certificate", err, "host", vc.host)
		return err
	}
	return nil
}

func (vp *Operator) ingressAdd(obj interface{}) {
	i := obj.(*v1beta1.Ingress)
	key, err := cache.MetaNamespaceKeyFunc(obj)
	if err != nil {
		vp.logger.LogError("couldn't add ingress", err, "key", i)
		return
	}
	vp.queue.AddRateLimited(key)
}

func (vp *Operator) ingressUpdate(old, cur interface{}) {
	iOld := old.(*v1beta1.Ingress)
	iCur := cur.(*v1beta1.Ingress)

	if !isIngressNeedsUpdate(iCur, iOld) {
		vp.logger.LogDebug("nothing changed. no need to update ingress", "key", keyFunc(iOld))
		return
	}

	key, err := cache.MetaNamespaceKeyFunc(cur)
	if err != nil {
		vp.logger.LogError("couldn't add ingress %s/%s", err, "key", keyFunc(iCur))
		return
	}
	vp.logger.LogDebug("ingress was updated", "key", key)
	vp.queue.AddRateLimited(key)
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
	vp.logger.LogDebug("added upstream secret", "key", keyFunc(secret))
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
	vp.logger.LogDebug("deleted upstream secret", "key", keyFunc(secret))
	return vp.waitForUpstreamSecret(secret, isSecretDeleted)
}

func (vp *Operator) updateUpstreamSecret(sCur, sOld *v1.Secret) error {
	if !isSecretNeedsUpdate(sCur, sOld) {
		vp.logger.LogDebug("nothing changed. no need to update secret", "key", keyFunc(sOld))
		return nil
	}
	vp.logger.LogDebug("updated upstream secret", keyFunc(sOld))
	_, err := vp.clientset.Secrets(sOld.GetNamespace()).Update(sCur)
	vp.eventRecorder.Eventf(sOld, v1.EventTypeNormal, UpdateEvent, fmt.Sprintf("updated tls certificate and key in secret %s", keyFunc(sOld)))
	return err
}

func (vp *Operator) updateUpstreamIngress(iOld, iCur *v1beta1.Ingress, conditionFunc watch.ConditionFunc) error {
	if reflect.DeepEqual(iOld.Spec, iCur.Spec) && reflect.DeepEqual(iOld.GetAnnotations(), iCur.GetAnnotations()) {
		vp.logger.LogDebug("nothing chanced. no need to update ingress", "key", keyFunc(iOld))
		return nil
	}
	ing, err := vp.clientset.ExtensionsV1beta1().Ingresses(iOld.GetNamespace()).Update(iCur)
	if err != nil {
		return err
	}

	vp.logger.LogInfo("updated upstream ingress", "key", keyFunc(iOld))
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
			vp.logger.LogError("couldn't add ingress", err, "key", keyFunc(i))
			return
		}
		vp.logger.LogDebug("added ingress", "key", key)
		vp.queue.Add(key)
	}
}

func (vp *Operator) secretDelete(obj interface{}) {
	secret := obj.(*v1.Secret)
	if ingress := vp.secretReferencedByIngress(secret); ingress != nil {
		vp.logger.LogDebug("secret was deleted. re-queueing ingress", "secret", keyFunc(secret), "ingress", keyFunc(ingress))
		key, err := cache.MetaNamespaceKeyFunc(ingress)
		if err != nil {
			vp.logger.LogError("couldn't add ingress", err, "key", keyFunc(ingress))
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
	if vp.RateLimit == -1 {
		return false
	}
	if n, ok := vp.rateLimitMap.LoadOrStore(viceCert.host, 1); ok {
		numRequests := n.(int)
		if numRequests >= vp.RateLimit {
			vp.logger.LogInfo("rate limit reached", "key", viceCert.getIngressKey(), "host", viceCert.host, "max requests", vp.RateLimit, "period", RateLimitPeriod)
			apiRateLimitHitGauge.With(prometheus.Labels{
				"ingress": viceCert.getIngressKey(),
				"host":    viceCert.host,
				"sans":    viceCert.getSANsString(),
			}).Set(1.0)
			return true
		}
		vp.rateLimitMap.Store(viceCert.host, numRequests+1)
	}
	return false
}
