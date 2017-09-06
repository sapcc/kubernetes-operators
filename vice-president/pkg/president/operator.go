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

	"errors"

	"encoding/base64"

	"fmt"
	"reflect"

	"strings"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/sapcc/go-vice"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
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
	ResyncPeriod = 5 * time.Second
	// CertificateRecheckInterval defines the period after which certificates are checked
	CertificateRecheckInterval = 15 * time.Second
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

	if err := options.CheckOptions(); err != nil {
		LogInfo(err.Error())
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

	operator.IngressInformer = IngressInformer
	operator.SecretInformer = SecretInformer

	return operator
}

// Run starts the operator
func (vp *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
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
		LogError("Failed to fetch key %s from cache: %s", key, err)
		return err
	}

	if !exists {
		LogInfo("Deleted ingress %#v", key)
		//TODO delete?
		return nil
	}

	ingress := o.(*v1beta1.Ingress)
	ingressAnnotations := ingress.GetAnnotations()

	if ingressAnnotations[vp.Options.IngressAnnotation] == "true" {

		for _, tls := range ingress.Spec.TLS {

			LogInfo("Checking Ingress %v/%v: Hosts: %v, Secret: %v/%v", ingress.GetNamespace(), ingress.GetName(), tls.Hosts, ingress.GetNamespace(), tls.SecretName)

			for _, host := range tls.Hosts {

				// check the secret. does it exist? does it contain a certificate and a key?
				// if not create empty secret in namespace of ingress and set to enrolling state
				viceCert, secret, err := vp.checkSecret(ingress, host, tls.SecretName)
				if err != nil {
					return err
				}
				viceCert.Host = host

				// if a certificate was found, validate it
				if viceCert.Certificate != nil {
					if err := vp.checkViceCertificate(viceCert, ingress); err != nil {
						return err
					}
				}

				// this one looks a little bit ugly:
				// try to pickup cert if TID and private key exist. cert is missing. ingress not in state enroll or renew.
				if tid := vp.ingressGetTIDForHost(ingress, viceCert.Host); tid != "" {
					viceCert.TID = tid
					if vp.ingressGetStateAnnotationForHost(ingress, viceCert.Host) != IngressStateEnroll || vp.ingressGetStateAnnotationForHost(ingress, viceCert.Host) != IngressStateRenew {
						if viceCert.PrivateKey != nil && viceCert.Certificate == nil {
							vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStatePickup)
						}
					} else {
						// make sure to avoid duplicate enroll/renew-requests for certificates if there's a TID
						vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateApprove)
					}
				}

				// StateMachine loop; done if state == IngressStateApproved
				for {
					if state := vp.ingressGetStateAnnotationForHost(ingress, viceCert.Host); state == IngressStateApproved {
						break
					}
					if err := vp.runStateMachine(ingress, secret, viceCert); err != nil {
						return err
					}
				}

			}
		}
	} else if len(ingressAnnotations) != 0 {
		LogDebug("Ignoring ingress %v/%v as annotation %s was set not found or set to false", ingress.GetNamespace(), ingress.GetName(), vp.Options.IngressAnnotation)
	} else {
		LogDebug("Ignoring ingress %v/%v as no annotations were found.", ingress.GetNamespace(), ingress.GetName())
	}
	return err
}

func (vp *Operator) runStateMachine(ingress *v1beta1.Ingress, secret *v1.Secret, viceCert *ViceCertificate) error {
	// labels for prometheus metrics
	labels := prometheus.Labels{
		"ingress": fmt.Sprintf("%s/%s", ingress.GetNamespace(), ingress.GetName()),
		"host":    viceCert.Host,
	}
	// add 0 to initialize the metrics that indicate failure
	initializeFailureMetrics(labels)

	// return an error if something is off to avoid a constant loop and give another ingress a chance
	switch state := vp.ingressGetStateAnnotationForHost(ingress, viceCert.Host); state {
	case IngressStateEnroll:
		if err := vp.enrollCertificate(viceCert); err != nil {
			LogInfo("Couldn't enroll new certificate for ingress %s/%s and host %s: %s", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, err)

			enrollFailedCounter.With(labels).Inc()

			return err
		}
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateApprove)
		vp.ingressSetTIDForHost(ingress, viceCert.Host, viceCert.TID)

		enrollSuccessCounter.With(labels).Inc()

	case IngressStateRenew:
		if err := vp.renewCertificate(viceCert); err != nil {
			LogInfo("Couldn't renew certificate for ingress %s/%s, host %s using TID %s: %s.", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, viceCert.TID, err)

			renewFailedCounter.With(labels).Inc()

			return err
		}
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateApprove)
		vp.ingressSetTIDForHost(ingress, viceCert.Host, viceCert.TID)

		renewSuccessCounter.With(labels).Inc()

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
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateApproved)
		vp.ingressSetTIDForHost(ingress, viceCert.Host, viceCert.TID)

		approveSuccessCounter.With(labels).Inc()

		if err := vp.updateCertificateInSecret(secret, viceCert); err != nil {
			return err
		}

	case IngressStatePickup:
		if err := vp.pickupCertificate(viceCert); err != nil {
			LogInfo("Couldn't pickup certificate for ingress %s/%s, host %s using TID %s: %s.", ingress.GetNamespace(), ingress.GetName(), viceCert.Host, viceCert.TID, err)

			pickupFailedCounter.With(labels).Inc()

			return err
		}
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateApproved)
		vp.ingressSetTIDForHost(ingress, viceCert.Host, viceCert.TID)

		pickupSuccessCounter.With(labels).Inc()

		if err := vp.updateCertificateInSecret(secret, viceCert); err != nil {
			return err
		}
	case IngressStateApproved:
		vp.ingressClearStateAndTIDAnnotationForHost(ingress, viceCert.Host)

	default:
		LogInfo("Checked certificate for ingress %s/%s", ingress.GetNamespace(), ingress.GetName())
	}
	return nil
}

func (vp *Operator) checkSecret(ingress *v1beta1.Ingress, host, secretName string) (*ViceCertificate, *v1.Secret, error) {

	obj, exists, err := vp.SecretInformer.GetStore().GetByKey(fmt.Sprintf("%s/%s", ingress.GetNamespace(), secretName))

	// does the secret exist?
	if exists != true {
		LogInfo("Secret %s/%s doesn't exist. Creating it and enrolling certificate", ingress.GetNamespace(), secretName)
		vp.ingressSetStateForHost(ingress, host, IngressStateEnroll)
		secret := vp.createEmptySecret(ingress.GetNamespace(), secretName)
		vp.addUpstreamSecret(secret)
		return &ViceCertificate{}, secret, nil
	}

	if checkError(err) != nil {
		if apierrors.IsNotFound(err) {
			LogInfo("Secret %s/%s doesn't exist. Creating it and enrolling certificate", ingress.GetNamespace(), secretName)
			vp.ingressSetStateForHost(ingress, host, IngressStateEnroll)
			secret := vp.createEmptySecret(ingress.GetNamespace(), secretName)
			vp.addUpstreamSecret(secret)
			return &ViceCertificate{}, secret, nil
		}
		LogInfo("Couldn't get secret %s/%s.", ingress.GetNamespace(), secretName)
		return &ViceCertificate{}, &v1.Secret{}, err
	}

	secret := obj.(*v1.Secret)

	// does the certificate exist? can it be decoded and parsed from the secret?
	viceCert, err := vp.getCertificateAndKeyFromSecret(secret)
	if err != nil {
		LogError(err.Error())
		vp.ingressSetStateForHost(ingress, host, IngressStateEnroll)
		return &ViceCertificate{}, secret, nil
	}
	return viceCert, secret, nil
}

// checkViceCertificate checks a given ViceCertificate and annotates the ingress accordingly
func (vp *Operator) checkViceCertificate(viceCert *ViceCertificate, ingress *v1beta1.Ingress) error {
	// does the secret contain the correct key for the certificate?
	if !viceCert.DoesKeyAndCertificateTally() {
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateRenew)
		return errors.New("Certificate and Key don't match. Renewing")
	}

	//  is the certificate for the correct host?
	if !viceCert.DoesCertificateAndHostMatch() {
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateEnroll)
		return errors.New("Certificate and Key don't match. Enrolling new one")
	}

	// is the certificate valid for time t ?
	if viceCert.DoesCertificateExpireSoon() {
		LogInfo("Certificate for host %s will expire in %s month. Renewing", viceCert.Host, CertificateRecheckInterval)
		vp.ingressSetStateForHost(ingress, viceCert.Host, IngressStateRenew)
	} else {
		LogInfo("Certificate for host %s is valid until %s", viceCert.Host, viceCert.Certificate.NotAfter.UTC())
	}
	return nil
}

// UpdateCertificateInSecret adds or updates the certificate in a secret
func (vp *Operator) updateCertificateInSecret(secret *v1.Secret, vc *ViceCertificate) error {
	updatedSecret, err := vp.addCertificateAndKeyToSecret(vc, secret)
	if err != nil {
		LogError("Couldn't update secret %s/%s: %s", secret.Namespace, secret.Name, err)
		return err
	}
	vp.updateUpstreamSecret(updatedSecret, secret)
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

// IngressSetStateForHost sets the state for an ingress and updates the upstream object; Annotation looks like <host>/vice-president-state : <state>
func (vp *Operator) ingressSetStateForHost(ingress *v1beta1.Ingress, host, state string) {
	updatedIngress, err := vp.ingressSetAnnotation(ingress, fmt.Sprintf("%s/%s", host, IngressStateAnnotation), state)
	if checkError(err) != nil {
		LogError(err.Error())
		return
	}
	vp.updateUpstreamIngress(updatedIngress, ingress)
}

// ingressSetTIDForHost sets the TID for an ingress and updates the upstream object; Annotation looks like  <host>/vice-president-tid : <tid>
func (vp *Operator) ingressSetTIDForHost(ingress *v1beta1.Ingress, host, tid string) {
	updatedIngress, err := vp.ingressSetAnnotation(ingress, fmt.Sprintf("%s/%s", host, IngressTIDAnnotation), tid)
	if checkError(err) != nil {
		LogError(err.Error())
		return
	}
	vp.updateUpstreamIngress(updatedIngress, ingress)
}

// IngressGetStateAnnotationForHost checks an ingress for vice-presidential annotations of the state of an host
func (vp *Operator) ingressGetStateAnnotationForHost(ingress *v1beta1.Ingress, host string) string {
	return vp.getIngressAnnotationForHost(ingress, host, IngressStateAnnotation)
}

func (vp *Operator) ingressClearStateAndTIDAnnotationForHost(ingress *v1beta1.Ingress, host string) {
	LogInfo("Removing state and TID annotation from ingress %s/%s for host %s",ingress.GetNamespace(),ingress.GetName(),host)

	o, err := api.Scheme.Copy(ingress)
	if err != nil {
		return
	}
	updatedIngress := o.(*v1beta1.Ingress)

	annotations := updatedIngress.GetAnnotations()
	if annotations == nil {
		return
	}
	delete(annotations, fmt.Sprintf("%s/%s", host, IngressStateAnnotation))
	delete(annotations, fmt.Sprintf("%s/%s", host, IngressTIDAnnotation))
	updatedIngress.SetAnnotations(annotations)

	vp.updateUpstreamIngress(updatedIngress, ingress)
}

func (vp *Operator) ingressSetAnnotation(ingress *v1beta1.Ingress, annotationKey, annotationValue string) (*v1beta1.Ingress, error) {
	LogInfo("Annotating ingress %s/%s with %s : %s", ingress.GetNamespace(), ingress.GetName(), annotationKey, annotationValue)

	o, err := api.Scheme.Copy(ingress)
	if err != nil {
		return nil, err
	}
	updatedIngress := o.(*v1beta1.Ingress)
	annotations := updatedIngress.GetAnnotations()
	if annotations == nil {
		annotations = map[string]string{}
	}
	annotations[annotationKey] = annotationValue

	updatedIngress.SetAnnotations(annotations)

	return updatedIngress, err
}

// ingressGetTIDAnnotationForHost checks an ingress for vice-presidential annotations of the TID of an host
func (vp *Operator) ingressGetTIDForHost(ingress *v1beta1.Ingress, host string) string {
	return vp.getIngressAnnotationForHost(ingress, host, IngressTIDAnnotation)
}

func (vp *Operator) getIngressAnnotationForHost(ingress *v1beta1.Ingress, host, annotationKey string) string {
	for k, v := range ingress.GetAnnotations() {
		if strings.Contains(k, annotationKey) && strings.Contains(k, host) {
			return v
		}
	}
	return ""
}

// GetCertificateAndKeyFromSecret extracts the certificate and private key from a given secrets spec
func (vp *Operator) getCertificateAndKeyFromSecret(secret *v1.Secret) (*ViceCertificate, error) {
	vc := &ViceCertificate{}
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
					vc.Certificate = nil
					continue
				}
				decodedCert := make([]byte, base64.StdEncoding.DecodedLen(len(v)))
				l, err := base64.StdEncoding.Decode(decodedCert, v)
				if err != nil {
					LogError("Couldn't decode base64 certificate: %s", err.Error())
					continue
				}
				if vc.Certificate, err = readCertificateFromPEM(decodedCert[:l]); err != nil {
					LogError(err.Error())
				}
			case SecretTLSKeyType:
				if v == nil || len(v) == 0 {
					LogInfo("Key in secret %s/%s is empty", secret.GetNamespace(), secret.GetName())
					vc.PrivateKey = nil
					continue
				}
				decodedKey := make([]byte, base64.StdEncoding.DecodedLen(len(v)))
				l, err := base64.StdEncoding.Decode(decodedKey, v)
				if err != nil {
					LogError("Couldn't decode base64 private key: %s", err.Error())
					continue
				}
				if vc.PrivateKey, err = readPrivateKeyFromPEM(decodedKey[:l]); err != nil {
					LogError(err.Error())
				}
			}
		}
	}
	if vc.Certificate == nil && vc.PrivateKey == nil {
		return nil, fmt.Errorf("Neither certificate nor private key found in secret: %s/%s", secret.Namespace, secret.Name)
	}
	return vc, nil
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

	encodedCert, err := base64EncodePEM(certPEM)
	if err != nil {
		return nil, err
	}

	encodedKey, err := base64EncodePEM(keyPEM)
	if err != nil {
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

	secret.Data[SecretTLSCertType] = encodedCert
	secret.Data[SecretTLSKeyType] = encodedKey

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
	i := obj.(*v1beta1.Ingress)
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
		LogInfo("Updated ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		vp.queue.Add(iCur)
		return
	}
	LogDebug("Nothing changed. No need to update ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
}

func (vp *Operator) updateUpstreamIngress(iCur, iOld *v1beta1.Ingress) {
	if vp.isIngressNeedsUpdate(iCur, iOld) {
		LogInfo("Updating upstream ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
		_, err := vp.Clientset.Ingresses(iOld.GetNamespace()).Update(iCur)
		if checkError(err) != nil {
			LogError(err.Error())
		}
	}
	LogDebug("No need to update upstream ingress %s/%s", iOld.GetNamespace(), iOld.GetName())
}

func (vp *Operator) addUpstreamSecret(secret *v1.Secret) {
	LogInfo("Added secret %s/%s", secret.GetNamespace(), secret.GetName())
	_, err := vp.Clientset.Secrets(secret.GetNamespace()).Create(secret)
	if checkError(err) != nil {
		LogError(err.Error())
	}
}

func (vp *Operator) deleteUpstreamSecret(secret *v1.Secret) {
	LogInfo("Deleted secret %s/%s", secret.GetNamespace(), secret.GetName())
	err := vp.Clientset.Secrets(secret.GetNamespace()).Delete(
		secret.GetName(),
		&meta_v1.DeleteOptions{},
	)
	if checkError(err) != nil {
		LogError(err.Error())
	}
}

func (vp *Operator) updateUpstreamSecret(sCur, sOld *v1.Secret) {
	if vp.isSecretNeedsUpdate(sCur, sOld) {
		LogInfo("Updated secret %s/%s", sOld.GetNamespace(), sOld.GetName())
		_, err := vp.Clientset.Secrets(sOld.GetNamespace()).Update(sCur)
		if checkError(err) != nil {
			LogError(err.Error())
		}
		return
	}
	LogInfo("Nothing changed. No need to update secret %s/%s", sOld.GetNamespace(), sOld.GetName())

}

func (vp *Operator) checkCertificates() {
	for _, o := range vp.IngressInformer.GetStore().List() {
		i := o.(*v1beta1.Ingress)
		LogDebug("Added ingress %s/%s", i.GetNamespace(), i.GetName())
		vp.queue.Add(i)
	}
}
