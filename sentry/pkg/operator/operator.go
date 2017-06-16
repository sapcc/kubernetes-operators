package operator

import (
	"fmt"
	"reflect"
	"sync"
	"time"

	sentry "github.com/atlassian/go-sentry-api"
	"github.com/golang/glog"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/fields"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"

	tprv1 "github.com/sapcc/kubernetes-operators/sentry/pkg/tpr/v1"
)

const (
	TPR_RECHECK_INTERVAL = 5 * time.Minute
	CACHE_RESYNC_PERIOD  = 2 * time.Minute
)

type Operator struct {
	Options

	clientset    *kubernetes.Clientset
	tprClient    *rest.RESTClient
	tprScheme    *runtime.Scheme
	tprInformer  cache.SharedIndexInformer
	queue        workqueue.RateLimitingInterface
	sentryClient *sentry.Client
	sentryOrg    sentry.Organization
}

func New(options Options) *Operator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	if err := CreateTPR(clientset); err != nil && !apierrors.IsAlreadyExists(err) {
		glog.Fatalf("Failed to create TPR resource: %s", err)
	}

	tprClient, scheme, err := NewClient(config)
	if err != nil {
		glog.Fatalf("Couldn't create TPR client: %s", err)
	}

	if err := WaitForSentyProjectResource(tprClient); err != nil {
		glog.Fatalf("Timout waiting for TPR to be ready")
	}

	sentryClient, err := sentry.NewClient(options.SentryToken, &options.SentryEndpoint, nil)
	if err != nil {
		glog.Fatalf("Failed to setup sentry spi client: %s", err)
	}

	operator := &Operator{
		Options:      options,
		clientset:    clientset,
		queue:        workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
		sentryClient: sentryClient,
		tprClient:    tprClient,
		tprScheme:    scheme,
	}

	tprInformer := cache.NewSharedIndexInformer(
		cache.NewListWatchFromClient(tprClient, tprv1.SentryProjectResourcePlural, metav1.NamespaceAll, fields.Everything()),
		&tprv1.SentryProject{},
		CACHE_RESYNC_PERIOD,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)
	tprInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.sentryProjectAdd,
		UpdateFunc: operator.sentryProjectUpdate,
		DeleteFunc: operator.sentryProjectDelete,
	})
	operator.tprInformer = tprInformer

	return operator
}

func (op *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer op.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)
	glog.Infof("Sentry operator started!  %v\n", VERSION)

	go op.tprInformer.Run(stopCh)

	glog.Info("Waiting for cache to sync...")
	cache.WaitForCacheSync(stopCh, op.tprInformer.HasSynced)
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

	project, ok := key.(*tprv1.SentryProject)
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

func (op *Operator) handler(key *tprv1.SentryProject) error {
	obj, exists, err := op.tprInformer.GetStore().Get(key)
	if err != nil {
		return fmt.Errorf("Failed to fetch key %s from cache: %s", key.Name, err)
	}
	if !exists {
		glog.Infof("Deleting project %s (not really, maybe in the future)", key.GetName())
	} else {
		tpr := obj.(*tprv1.SentryProject)
		if err := tpr.Spec.Validate(); err != nil {
			glog.V(3).Infof("Resource %s has an invalid spec: %s", tpr.Name, err)
			op.updateStatus(tpr, tprv1.SentryProjectError, err.Error())
			return nil
		}
		_, err := op.ensureProject(tpr.Spec.Team, tpr.Spec.Name)
		if err != nil {
			op.updateStatus(tpr, tprv1.SentryProjectError, err.Error())
			return fmt.Errorf("Failed to create project %s/%s: %s", tpr.Spec.Name, tpr.Spec.Team, err)
		}
		clientKey, err := op.ensureClientKey(tpr.Spec.Name, "k8s-operator")
		if err != nil {
			op.updateStatus(tpr, tprv1.SentryProjectError, err.Error())
			return fmt.Errorf("Failed to create client key for project %s: %s", tpr.Spec.Name, err)
		}
		secretData := map[string]string{
			fmt.Sprintf("%s.DSN", tpr.Spec.Name):        clientKey.DSN.Secret,
			fmt.Sprintf("%s.DSN.public", tpr.Spec.Name): clientKey.DSN.Public,
		}

		secret, err := op.clientset.Secrets(tpr.Namespace).Get("sentry", metav1.GetOptions{})
		if apierrors.IsNotFound(err) {
			glog.Infof("Creating secret %s/%s", "sentry", tpr.Namespace)
			_, err := op.clientset.Secrets(tpr.Namespace).Create(&v1.Secret{ObjectMeta: metav1.ObjectMeta{Name: "sentry"}, StringData: secretData})
			if err != nil {
				op.updateStatus(tpr, tprv1.SentryProjectError, err.Error())
			}
			return err
		}
		if err != nil {
			op.updateStatus(tpr, tprv1.SentryProjectError, err.Error())
			return err
		}
		updated := false
		for key, value := range secretData {
			if b, ok := secret.Data[key]; !ok || string(b) != value {
				updated = true
			}
		}
		if updated {
			glog.Infof("Updating key %s in secret %s/%s", tpr.Spec.Name, "sentry", tpr.Namespace)
			secret.StringData = secretData
			if _, err := op.clientset.Secrets(tpr.Namespace).Update(secret); err != nil {
				op.updateStatus(tpr, tprv1.SentryProjectError, err.Error())
				return err
			}
		}
		op.updateStatus(tpr, tprv1.SentryProjectProcessed, "Project processed")
	}
	return nil
}

func (op *Operator) sentryProjectAdd(obj interface{}) {
	proj := obj.(*tprv1.SentryProject)
	glog.Infof("Added sentry project %s/%s", proj.GetName(), proj.GetNamespace())
	op.queue.Add(proj)
}

func (op *Operator) sentryProjectDelete(obj interface{}) {
	proj := obj.(*tprv1.SentryProject)
	glog.Infof("Deleted sentry project %s/%s", proj.GetName(), proj.GetNamespace())
	op.queue.Add(proj)
}

func (op *Operator) sentryProjectUpdate(cur, old interface{}) {
	curProj := cur.(*tprv1.SentryProject)
	oldProj := old.(*tprv1.SentryProject)
	if !reflect.DeepEqual(oldProj.Spec, curProj.Spec) {
		glog.Infof("Updated sentry project %s/%s", curProj.GetName(), curProj.GetNamespace())
		op.queue.Add(curProj)
	}
}

func (op *Operator) updateStatus(tpr *tprv1.SentryProject, state tprv1.SentryProjectState, message string) error {
	r, err := op.tprScheme.Copy(tpr)
	if err != nil {
		return err
	}
	tpr = r.(*tprv1.SentryProject)
	tpr.Status.Message = message
	tpr.Status.State = state

	return op.tprClient.Put().
		Name(tpr.ObjectMeta.Name).
		Namespace(tpr.ObjectMeta.Namespace).
		Resource(tprv1.SentryProjectResourcePlural).
		Body(tpr).
		Do().
		Error()
}
