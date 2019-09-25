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
	"strings"
	"sync"
	"time"

	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/kubernetes-operators/vice-president/pkg/log"
	corev1 "k8s.io/api/core/v1"
	extensionsv1beta1 "k8s.io/api/extensions/v1beta1"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	corev1Informers "k8s.io/client-go/informers/core/v1"
	v1beta1Informers "k8s.io/client-go/informers/extensions/v1beta1"
	"k8s.io/client-go/kubernetes/scheme"
	kubernetesCoreV1 "k8s.io/client-go/kubernetes/typed/core/v1"
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
	resyncInterval           time.Duration // ResyncInterval defines the period after which the local cache of ingresses is refreshed.
	certificateCheckInterval time.Duration // CertificateCheckInterval defines the period after which certificates are checked.
	clientset                *k8sFramework
	viceClient               *viceClient
	ingressInformer          cache.SharedIndexInformer
	secretInformer           cache.SharedIndexInformer
	queue                    workqueue.RateLimitingInterface
	logger                   log.Logger
	eventRecorder            record.EventRecorder
	rateLimitMap             sync.Map // stores mapping of { host <string> : numAPIRequests <int>}
}

// New creates a new operator using the given options
func New(options Options, logger log.Logger) *Operator {
	viceLogger := log.NewLoggerWith(logger, "component", "viceClient")
	operatorLogger := log.NewLoggerWith(logger, "component", "operator")
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

	clientset, err := newK8sFramework(config, logger)
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
	b.StartRecordingToSink(&kubernetesCoreV1.EventSinkImpl{
		Interface: clientset.CoreV1().Events(""),
	})
	eventRecorder := b.NewRecorder(scheme.Scheme, corev1.EventSource{
		Component: EventComponent,
	})

	queue := workqueue.NewRateLimitingQueue(
		workqueue.NewItemExponentialFailureRateLimiter(30*time.Second, 600*time.Second),
	)

	ingressInformer := v1beta1Informers.NewIngressInformer(
		clientset.Clientset,
		options.Namespace,
		options.ResyncInterval,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	ingressInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: func(obj interface{}) {
			i := obj.(*extensionsv1beta1.Ingress)
			key, err := cache.MetaNamespaceKeyFunc(obj)
			if err != nil {
				clientset.logger.LogError("couldn't add ingress", err, "key", i)
				return
			}
			queue.AddRateLimited(key)
		},
		UpdateFunc: func(oldObj, newObj interface{}) {
			iOld := oldObj.(*extensionsv1beta1.Ingress)
			iNew := newObj.(*extensionsv1beta1.Ingress)

			if !isIngressNeedsUpdate(iNew, iOld) {
				clientset.logger.LogDebug("nothing changed. no need to update ingress", "key", keyFunc(iOld))
				return
			}

			key, err := cache.MetaNamespaceKeyFunc(iNew)
			if err != nil {
				clientset.logger.LogError("couldn't add ingress %s/%s", err, "key", keyFunc(iNew))
				return
			}
			clientset.logger.LogDebug("ingress was updated", "key", key)
			queue.AddRateLimited(key)
		},
	})

	secretInformer := corev1Informers.NewSecretInformer(
		clientset.Clientset,
		options.Namespace,
		options.ResyncInterval,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	secretInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		DeleteFunc: func(obj interface{}) {
			secret := obj.(*corev1.Secret)
			// If secret is deleted but used by an ingress, requeue the ingress.
			if ingressKey, ok := secret.GetAnnotations()[AnnotationSecretClaimedByIngress]; ok {
				clientset.logger.LogDebug("secret was deleted. re-queueing ingress", "secret", keyFunc(secret), "ingress", keyFunc(ingressKey))
				queue.AddAfter(ingressKey, BaseDelay)
			}
		},
	})

	return &Operator{
		queue:                    queue,
		ingressInformer:          ingressInformer,
		secretInformer:           secretInformer,
		logger:                   operatorLogger,
		Options:                  options,
		clientset:                clientset,
		vicePresidentConfig:      vicePresidentConfig,
		viceClient:               viceClient,
		rootCertPool:             rootCertPool,
		intermediateCertificate:  intermediateCert,
		resyncInterval:           options.ResyncInterval,
		certificateCheckInterval: options.CertificateCheckInterval,
		eventRecorder:            eventRecorder,
		rateLimitMap:             sync.Map{},
	}
}

// Run starts the operator.
func (vp *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer utilruntime.HandleCrash()
	defer vp.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)

	vp.logger.LogInfo("Ladies and Gentlemen, the Vice President! Renewing your Digicert certificates.", "version", VERSION)

	go vp.ingressInformer.Run(stopCh)
	go vp.secretInformer.Run(stopCh)

	vp.logger.LogInfo("waiting for cache to sync...")
	if !cache.WaitForCacheSync(
		stopCh,
		vp.ingressInformer.HasSynced,
		vp.secretInformer.HasSynced,
	) {
		utilruntime.HandleError(errors.New("timed out while waiting for caches to sync"))
		return
	}

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
	vp.logger.LogInfo("vice president is resigning")
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

	ingress := o.(*extensionsv1beta1.Ingress)
	// return right here if ingress is not annotated with vice-president: true
	if !isIngressHasAnnotation(ingress, AnnotationVicePresident) {
		vp.logger.LogDebug("ignoring ingress as vice-presidential annotation is not set", "key", key)
		return nil
	}
	// Check each host.
	for _, tls := range ingress.Spec.TLS {
		if len(tls.Hosts) == 0 {
			return fmt.Errorf("no hosts found in ingress.spec.tls. key %s", key)
		}

		// Use the given name or the normalized hostname for the secret name.
		secretName := tls.SecretName
		if secretName == "" {
			return fmt.Errorf("no secret name given in ingress %s for host %s", key, tls.Hosts[0])
		}

		vp.logger.LogDebug("checking ingress", "key", key, "hosts", strings.Join(tls.Hosts, ", "), "secret", secretKey(ingress.GetNamespace(), secretName))

		// The tls.Hosts[0] will be the CN, tls.Hosts[1:] the SANs of the certificate.
		vc := NewViceCertificate(ingress, secretName, tls.Hosts[0], tls.Hosts[1:], vp.intermediateCertificate, vp.rootCertPool)
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
			if err := vp.viceClient.enroll(vc); err != nil {
				vp.logger.LogError("couldn't enroll certificate", err, "key", vc.getIngressKey(), "host", vc.host)
				enrollFailedCounter.With(labels).Inc()
				return err
			}
			enrollSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStateRenew:
			if err := vp.renewCertificateRateLimited(vc); err != nil {
				vp.logger.LogError("couldn't renew certificate", err, "key", vc.getIngressKey(), "host", vc.host, "tid", vc.tid)
				renewFailedCounter.With(labels).Inc()
				return err
			}
			renewSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStatePickup:
			if err := vp.pickupCertificateRateLimited(vc); err != nil {
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
			if err := vp.replaceCertificateRateLimited(vc); err != nil {
				vp.logger.LogError("couldn't replace certificate", err, "key", vc.getIngressKey(), "host", vc.host, "tid", vc.tid)
				replaceFailedCounter.With(labels).Inc()
				return err
			}
			// Remove the vice-president/replace-cert annotation from the ingress if all certificates have been replaced.
			if isLastHostInIngressSpec(vc.ingress, vc.host) {
				if err := vp.clientset.removeIngressAnnotation(vc.ingress, AnnotationCertificateReplacement); err != nil {
					return err
				}
			}
			replaceSuccessCounter.With(labels).Inc()
			nextState = IngressStateApprove

		case IngressStateApprove:
			if vc.certificate != nil && vc.tid == "" {
				vp.logger.LogInfo("certificate was automatically approved", "key", vc.getIngressKey(), "host", vc.host)
			} else {
				if err := vp.viceClient.approve(vc); err != nil {
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
			vp.eventRecorder.Eventf(vc.ingress, corev1.EventTypeNormal, UpdateEvent, fmt.Sprintf("updated certificate for host %s, ingress %s", vc.host, vc.getIngressKey()))
			nextState = IngressStateApproved

		case IngressStateApproved:
			// Certificate approved. We're done.
			return nil

		default:
			secret, err := vp.clientset.getOrCreateSecret(vc.ingress.GetNamespace(), vc.secretName, vc.ingress.GetLabels(), map[string]string{AnnotationSecretClaimedByIngress: vc.getIngressKey()})
			if err != nil {
				return errors.Wrapf(err, "couldn't get nor create secret %s", vc.getSecretKey())
			}

			// Check if the given Secret is already being claimed (aka used) by another Ingress. If so, return here and leave it to the ingress that came first.
			// Multiple references to a secret can be intentional to re-use the certificate or due to misconfiguration if the host differs.
			// In the latter case we prevent the operator from enrolling new certificates over and and over again.
			if claimedByIngress, isClaimedByAnotherIngress := isSecretClaimedByAnotherIngress(secret, vc.getIngressKey()); isClaimedByAnotherIngress {
				vp.logger.LogInfo("cannot use secret. already in use by another ingress", "secret", vc.getSecretKey(), "claimedByIngress", claimedByIngress, "ingress", vc.getIngressKey())
				return nil
			}

			// Get the certificate and private key from the secret.
			vc.certificate, vc.privateKey = getCertificateAndKeyFromSecret(secret, tlsKeySecretKey, tlsCertSecretKey)

			// Add finalizer before creating anything. Return error if this fails.
			if err := vp.clientset.ensureVicePresidentFinalizerExists(vc.ingress); err != nil {
				return errors.Wrapf(err, "will not create certificate in this cycle. failed to add finalizer %v", FinalizerVicePresident)
			}

			// There was an attempt to delete the ingress. Remove the claim on the secret and the finalizer.
			if ingressHasDeletionTimestamp(vc.ingress) {
				if err := vp.clientset.removeSecretAnnotation(secret, AnnotationSecretClaimedByIngress); err != nil {
					return err
				}
				return vp.clientset.ensureVicePresidentFinalizerRemoved(vc.ingress)
			}

			nextState = vp.getNextState(vc)
		}
	}
	return nil
}

func (vp *Operator) getNextState(vc *ViceCertificate) string {
	if vc.certificate == nil && vc.privateKey == nil {
		vp.logger.LogInfo("no certificate and/or key found in secret", "key", vc.getSecretKey(), "host", vc.host)
		return IngressStateEnroll
	}

	if isIngressHasAnnotation(vc.ingress, AnnotationCertificateReplacement) {
		vp.logger.LogInfo("annotation found on ingress. replacing certificate", "annotation", AnnotationCertificateReplacement, "ingress", vc.getIngressKey(), "host", vc.host)
		return IngressStateReplace
	}

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
		vp.logger.LogInfo("certificate will expire soon", "host", vc.host, "expiresInLessThan", vp.MinCertValidityDays)
		return IngressStateRenew
	}

	if vc.IsRevoked() {
		vp.logger.LogInfo("certificate is revoked", "host", vc.host)
		return IngressStateReplace
	}

	vp.logger.LogInfo("certificate ist valid", "host", vc.host, "validUntil", vc.certificate.NotAfter.UTC().String())
	return IngressStateApproved
}

// updateCertificateInSecret adds or updates the certificate in a secret
func (vp *Operator) updateCertificateAndKeyInSecret(vc *ViceCertificate, tlsKeySecretKey, tlsCertSecretKey string) error {
	secret, err := vp.clientset.getOrCreateSecret(vc.ingress.GetNamespace(), vc.secretName, vc.ingress.GetLabels(), map[string]string{AnnotationSecretClaimedByIngress: vc.getIngressKey()})
	if err != nil {
		return err
	}

	vp.logger.LogInfo("add/update certificate to secret", "key", vc.getSecretKey())

	updatedSecret, err := addCertificateAndKeyToSecret(vc, secret, tlsKeySecretKey, tlsCertSecretKey)
	if err != nil {
		vp.logger.LogError("couldn't update secret", err, "key", vc.getSecretKey())
		return err
	}

	if updatedSecret.Annotations == nil {
		updatedSecret.Annotations = map[string]string{}
	}

	// Set a claim on the secret for the ingress to prevent other ingress from using it as well.
	updatedSecret.Annotations[AnnotationSecretClaimedByIngress] = vc.getIngressKey()
	return vp.clientset.updateSecret(secret, updatedSecret)
}

func (vp *Operator) checkCertificates() {
	for _, o := range vp.ingressInformer.GetStore().List() {
		i := o.(*extensionsv1beta1.Ingress)
		key, err := cache.MetaNamespaceKeyFunc(o)
		if err != nil {
			vp.logger.LogError("couldn't add ingress", err, "key", keyFunc(i))
			return
		}
		vp.logger.LogDebug("added ingress", "key", key)
		vp.queue.Add(key)
	}
}

func (vp *Operator) secretReferencedByIngress(secret *corev1.Secret) *extensionsv1beta1.Ingress {
	for _, iObj := range vp.ingressInformer.GetStore().List() {
		ingress := iObj.(*extensionsv1beta1.Ingress)
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

// enrollCertificateRateLimited triggers the enrollment of a certificate if rate limit is not exceeded
func (vp *Operator) enrollCertificateRateLimited(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	return vp.viceClient.enroll(vc)
}

// renewCertificateRateLimited triggers the renewal of a certificate if rate limit is not exceeded
func (vp *Operator) renewCertificateRateLimited(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	return vp.viceClient.renew(vc)
}

// pickupCertificateRateLimited picks up a given certificate if rate limit is not exceeded
func (vp *Operator) pickupCertificateRateLimited(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	return vp.viceClient.pickup(vc)
}

// replaceCertificateRateLimited triggers the replacement of the certificate if rate limit is not exceeded
func (vp *Operator) replaceCertificateRateLimited(vc *ViceCertificate) error {
	if vp.isRateLimitForHostExceeded(vc) {
		return nil
	}
	return vp.viceClient.replace(vc)
}
