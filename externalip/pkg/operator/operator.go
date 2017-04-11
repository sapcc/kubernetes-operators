package operator

import (
	"net"
	"os/exec"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/golang/glog"
	meta_v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/pkg/api/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/workqueue"
	"k8s.io/kubernetes/pkg/util/wait"
)

const SERVICE_RECHECK_INTERVAL = 5 * time.Second

var (
	resyncPeriod = 10 * time.Minute
	VERSION      = "0.0.0.dev"
)

type Options struct {
	KubeConfig       string
	NetworkInterface string
	IgnoreCIDR       []net.IPNet
}

type Operator struct {
	Options

	clientset       *kubernetes.Clientset
	serviceInformer cache.SharedIndexInformer
	queue           workqueue.RateLimitingInterface
}

func New(options Options) *Operator {
	config := newClientConfig(options)

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	operator := &Operator{
		Options:   options,
		clientset: clientset,
		queue:     workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
	}

	serviceInformer := cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options meta_v1.ListOptions) (runtime.Object, error) {
				return clientset.Services(v1.NamespaceAll).List(meta_v1.ListOptions{})
			},
			WatchFunc: func(options meta_v1.ListOptions) (watch.Interface, error) {
				return clientset.Services(v1.NamespaceAll).Watch(meta_v1.ListOptions{})
			},
		},
		&v1.Service{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)

	serviceInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.serviceAdd,
		UpdateFunc: operator.serviceUpdate,
		DeleteFunc: operator.serviceDelete,
	})
	operator.serviceInformer = serviceInformer

	return operator
}

func newClientConfig(options Options) *rest.Config {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	overrides := &clientcmd.ConfigOverrides{}

	if options.KubeConfig != "" {
		rules.ExplicitPath = options.KubeConfig
	}

	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, overrides).ClientConfig()
	if err != nil {
		glog.Fatalf("Couldn't get Kubernetes default config: %s", err)
	}

	return config
}

func (op *Operator) Run(threadiness int, stopCh <-chan struct{}, wg *sync.WaitGroup) {
	defer op.queue.ShutDown()
	defer wg.Done()
	wg.Add(1)
	glog.Info("External IP operator started!  %v\n", VERSION)

	go op.serviceInformer.Run(stopCh)

	glog.Info("Waiting for cache to sync...")
	cache.WaitForCacheSync(stopCh, op.serviceInformer.HasSynced)
	glog.Info("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(op.runWorker, time.Second, stopCh)
	}

	//ticker := time.NewTicker(SERVICE_RECHECK_INTERVAL)
	//go func() {
	//  for {
	//    select {
	//    case <-ticker.C:
	//      glog.Info("Next check in %v", SERVICE_RECHECK_INTERVAL)
	//      vp.externalIPs()
	//    case <-stopCh:
	//      ticker.Stop()
	//      return
	//    }
	//  }
	//}()

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

	// do your work on the key.  This method will contains your "do stuff" logic
	err := op.syncHandler(key)
	if err == nil {
		op.queue.Forget(key)
		return true
	}

	glog.Warningf("Error running syncHandler: %v", err)
	op.queue.AddRateLimited(key)

	return true
}

func (op *Operator) syncHandler(key interface{}) error {
	store := op.serviceInformer.GetStore()
	attachedIPs, err := op.existingIPs()
	if err != nil {
		return err
	}
	externalIPs := map[string]bool{}
	for _, obj := range store.List() {
		svc := obj.(*v1.Service)
		for _, ip := range svc.Spec.ExternalIPs {
			externalIPs[ip] = true
		}
	}
	//add missing ips
	for ip, _ := range externalIPs {
		if _, ok := attachedIPs[ip]; !ok && !op.ignoreAddress(ip) {
			glog.Infof("Adding %s to interface %s", ip, op.NetworkInterface)
			_, err := exec.Command("ip", "addr", "add", ip, "dev", op.NetworkInterface).CombinedOutput()
			if err != nil {
				return err
			}
		}
	}
	//remove missing ips
	for ip, _ := range attachedIPs {
		if _, ok := externalIPs[ip]; !ok && !op.ignoreAddress(ip) {
			glog.Infof("Removing %s from interface %s", ip, op.NetworkInterface)
			_, err := exec.Command("ip", "addr", "del", ip, "dev", op.NetworkInterface).CombinedOutput()
			if err != nil {
				return err
			}
		}
	}

	return nil
}

func (op *Operator) ignoreAddress(ipstring string) bool {
	ip := net.ParseIP(ipstring)
	if ip == nil {
		glog.V(3).Infof("Ignore invalid ip: %s", ipstring)
		return true
	}
	for _, ipnet := range op.Options.IgnoreCIDR {
		if ipnet.Contains(ip) {
			glog.V(3).Infof("Ignore ip %s, blacklisted by %s", ipstring, ipnet.String())
			return true
		}
	}
	return false
}

func (op *Operator) existingIPs() (map[string]bool, error) {
	intf, err := net.InterfaceByName(op.NetworkInterface)
	if err != nil {
		return nil, err
	}
	addresses, err := intf.Addrs()
	if err != nil {
		return nil, err
	}
	ips := make(map[string]bool, len(addresses))
	for _, address := range addresses {
		t := strings.SplitN(address.String(), "/", 2)
		if len(t) == 0 || t[0] == "" {
			continue
		}
		ips[t[0]] = true
	}
	return ips, nil

}

func (op *Operator) serviceAdd(obj interface{}) {
	svc := obj.(*v1.Service)
	if len(svc.Spec.ExternalIPs) == 0 {
		return
	}
	glog.V(2).Info("Added service with external IPs: ", svc.GetName())
	op.queue.Add(svc)
}

func (op *Operator) serviceDelete(obj interface{}) {
	svc := obj.(*v1.Service)
	if len(svc.Spec.ExternalIPs) == 0 {
		return
	}
	glog.V(2).Info("Removed service with external IPs: ", svc.GetName())
	op.queue.Add(svc)
}

func (op *Operator) serviceUpdate(cur, old interface{}) {
	curSvc := cur.(*v1.Service)
	oldSvc := old.(*v1.Service)
	// No changes to externalIPs
	if reflect.DeepEqual(curSvc.Spec.ExternalIPs, oldSvc.Spec.ExternalIPs) {
		return
	}
	glog.V(2).Info("Changed external IPs of service: ", curSvc.GetName())
	op.queue.Add(curSvc)
}
