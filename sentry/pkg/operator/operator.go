package operator

import (
	"context"
	"fmt"
	"reflect"
	"sync"
	"time"

	sentry "github.com/atlassian/go-sentry-api"
	"github.com/golang/glog"
	v1 "github.com/sapcc/kubernetes-operators/sentry/pkg/apis/sentry/v1"
	corev1 "k8s.io/api/core/v1"
	apiextensionsclient "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"

	sentryclientset "github.com/sapcc/kubernetes-operators/sentry/pkg/client/clientset/versioned"
	sentryinformerv1 "github.com/sapcc/kubernetes-operators/sentry/pkg/client/informers/externalversions/sentry/v1"
)

const (
	TPR_RECHECK_INTERVAL = 5 * time.Minute
	CACHE_RESYNC_PERIOD  = 2 * time.Minute
)

type Operator struct {
	Options

	clientset       *kubernetes.Clientset
	sentryClientset sentryclientset.Interface
	sentryInformer  cache.SharedIndexInformer
	queue           workqueue.RateLimitingInterface
	sentryClient    *sentry.Client
	sentryOrg       sentry.Organization
}

func New(options Options) *Operator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	apiextensionsclientset, err := apiextensionsclient.NewForConfig(config)
	if err != nil {
		glog.Errorf("Failed to create apiextenstionsclient: %s", err)
	}

	if err := EnsureCRD(apiextensionsclientset); err != nil && !apierrors.IsAlreadyExists(err) {
		glog.Fatalf("Failed to create CRD resource: %s", err)
	}

	sentryClientset, err := sentryclientset.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create CRD client: %s", err)
	}

	var timeout int = 10
	sentryClient, err := sentry.NewClient(options.SentryToken, &options.SentryEndpoint, &timeout)
	if err != nil {
		glog.Fatalf("Failed to setup sentry api client: %s", err)
	}

	operator := &Operator{
		Options:         options,
		clientset:       clientset,
		queue:           workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
		sentryClient:    sentryClient,
		sentryClientset: sentryClientset,
	}

	sentryInformer := sentryinformerv1.NewSentryProjectInformer(sentryClientset, metav1.NamespaceAll, CACHE_RESYNC_PERIOD, cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc})

	sentryInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.sentryProjectAdd,
		UpdateFunc: operator.sentryProjectUpdate,
		DeleteFunc: operator.sentryProjectDelete,
	})
	operator.sentryInformer = sentryInformer

	return operator
}

func (op *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer op.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)
	glog.Infof("Sentry operator started!  %v\n", VERSION)

	go op.sentryInformer.Run(stopCh)

	glog.Info("Waiting for cache to sync...")
	cache.WaitForCacheSync(stopCh, op.sentryInformer.HasSynced)
	glog.Info("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(op.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(TPR_RECHECK_INTERVAL)
	go func() {
		for {
			select {
			case <-ticker.C:
				glog.V(2).Infof("Next reconciliation check in %v (FIXME)", TPR_RECHECK_INTERVAL)
				//op.queue.Add(true)
			case <-stopCh:
				ticker.Stop()
				return
			}
		}
	}()

	<-stopCh
}

func (op *Operator) runWorker() {
	for op.processNextWorkItem() {
	}
}

func (op *Operator) processNextWorkItem() bool {
	key, quit := op.queue.Get()
	if quit {
		return false
	}
	defer op.queue.Done(key)

	project, ok := key.(*v1.SentryProject)
	if !ok {
		glog.Warningf("Skipping work item of unexpected type: %v", key)
		op.queue.Forget(key)
		return true
	}
	err := op.handler(project)
	if err == nil {
		op.queue.Forget(key)
		return true
	}

	glog.Warningf("Error running handler: %v", err)
	op.queue.AddRateLimited(key)

	return true
}

func (op *Operator) handler(key *v1.SentryProject) error {
	obj, exists, err := op.sentryInformer.GetStore().Get(key)
	if err != nil {
		return fmt.Errorf("Failed to fetch key %s from cache: %s", key.Name, err)
	}
	if !exists {
		glog.Infof("Deleting project %s (not really, maybe in the future)", key.GetName())
	} else {
		project := obj.(*v1.SentryProject)
		if err := project.Spec.Validate(); err != nil {
			glog.V(3).Infof("Resource %s has an invalid spec: %s", project.Name, err)
			op.updateStatus(project, v1.SentryProjectError, err.Error())
			return nil
		}
		_, err := op.ensureProject(project.Spec.Team, project.Spec.Name)
		if err != nil {
			op.updateStatus(project, v1.SentryProjectError, err.Error())
			return fmt.Errorf("Failed to create project %s/%s: %s", project.Spec.Name, project.Spec.Team, err)
		}
		clientKey, err := op.ensureClientKey(project.Spec.Name, "k8s-operator")
		if err != nil {
			op.updateStatus(project, v1.SentryProjectError, err.Error())
			return fmt.Errorf("Failed to create client key for project %s: %s", project.Spec.Name, err)
		}
		secretData := map[string]string{
			fmt.Sprintf("%s.DSN", project.Spec.Name):               clientKey.DSN.Secret,
			fmt.Sprintf("%s.DSN.public", project.Spec.Name):        clientKey.DSN.Public,
			fmt.Sprintf("%s.DSN.python", project.Spec.Name):        fmt.Sprintf("requests+%s?verify_ssl=0", clientKey.DSN.Secret),
			fmt.Sprintf("%s.DSN.public.python", project.Spec.Name): fmt.Sprintf("requests+%s?verify_ssl=0", clientKey.DSN.Public),
		}

		secret, err := op.clientset.CoreV1().Secrets(project.Namespace).Get(context.TODO(), "sentry", metav1.GetOptions{})
		if apierrors.IsNotFound(err) {
			glog.Infof("Creating secret %s/%s", "sentry", project.Namespace)
			_, err := op.clientset.CoreV1().Secrets(project.Namespace).Create(context.TODO(), &corev1.Secret{ObjectMeta: metav1.ObjectMeta{Name: "sentry"}, StringData: secretData}, metav1.CreateOptions{})
			if err != nil {
				op.updateStatus(project, v1.SentryProjectError, err.Error())
			}
			return err
		}
		if err != nil {
			op.updateStatus(project, v1.SentryProjectError, err.Error())
			return err
		}
		updated := false
		for key, value := range secretData {
			if b, ok := secret.Data[key]; !ok || string(b) != value {
				updated = true
			}
		}
		if updated {
			glog.Infof("Updating key %s in secret %s/%s", project.Spec.Name, "sentry", project.Namespace)
			secret.StringData = secretData
			if _, err := op.clientset.CoreV1().Secrets(project.Namespace).Update(context.TODO(), secret, metav1.UpdateOptions{}); err != nil {
				op.updateStatus(project, v1.SentryProjectError, err.Error())
				return err
			}
		}
		op.updateStatus(project, v1.SentryProjectProcessed, "Project processed")
	}
	return nil
}

func (op *Operator) sentryProjectAdd(obj interface{}) {
	proj := obj.(*v1.SentryProject)
	glog.Infof("Added sentry project %s/%s", proj.GetName(), proj.GetNamespace())
	op.queue.Add(proj)
}

func (op *Operator) sentryProjectDelete(obj interface{}) {
	proj := obj.(*v1.SentryProject)
	glog.Infof("Deleted sentry project %s/%s", proj.GetName(), proj.GetNamespace())
	op.queue.Add(proj)
}

func (op *Operator) sentryProjectUpdate(cur, old interface{}) {
	curProj := cur.(*v1.SentryProject)
	oldProj := old.(*v1.SentryProject)
	if !reflect.DeepEqual(oldProj.Spec, curProj.Spec) {
		glog.Infof("Updated sentry project %s/%s", curProj.GetName(), curProj.GetNamespace())
		op.queue.Add(curProj)
	}
}

func (op *Operator) updateStatus(project *v1.SentryProject, state v1.SentryProjectState, message string) error {
	project = project.DeepCopy()
	project.Status.Message = message
	project.Status.State = state

	_, err := op.sentryClientset.SentryV1().SentryProjects(project.Namespace).Update(context.TODO(), project, metav1.UpdateOptions{})
	return err
}
