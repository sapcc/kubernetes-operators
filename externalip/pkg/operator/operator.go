package operator

import (
	"bytes"
	"net"
	"os/exec"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/golang/glog"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/wait"
	informers_core_v1 "k8s.io/client-go/informers/core/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/workqueue"
)

const (
	SERVICE_RECHECK_INTERVAL = 1 * time.Minute
)

var (
	resyncPeriod        = 10 * time.Minute
	VERSION             = "HEAD"
	IgnoreSvcAnnotation = "externalip.sap.cc/ignore"
)

type Options struct {
	KubeConfig       string
	NetworkInterface string
	IgnoreCIDR       []net.IPNet
	SourceAddress    string
}

type Operator struct {
	Options

	clientset         *kubernetes.Clientset
	serviceInformer   cache.SharedIndexInformer
	endpointsInformer cache.SharedIndexInformer
	queue             workqueue.RateLimitingInterface
}

func New(options Options) *Operator {
	var config *rest.Config
	var err error
	if options.KubeConfig == "" {
		config, err = rest.InClusterConfig()
		if err != nil {
			glog.Fatalf("Couldn't create in-cluster config: %s", err)
		}
	} else {
		config = newClientConfig(options)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		glog.Fatalf("Couldn't create Kubernetes client: %s", err)
	}

	operator := &Operator{
		Options:           options,
		clientset:         clientset,
		queue:             workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter()),
		serviceInformer:   informers_core_v1.NewServiceInformer(clientset, "", resyncPeriod, nil),
		endpointsInformer: informers_core_v1.NewEndpointsInformer(clientset, "", resyncPeriod, nil),
	}

	operator.serviceInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    operator.serviceAdd,
		UpdateFunc: operator.serviceUpdate,
		DeleteFunc: operator.serviceDelete,
	})
	operator.endpointsInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		UpdateFunc: operator.endpointsUpdate,
	})

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
	glog.Infof("External IP operator started!  %v\n", VERSION)

	go op.serviceInformer.Run(stopCh)
	go op.endpointsInformer.Run(stopCh)

	glog.Info("Waiting for caches to sync...")
	cache.WaitForCacheSync(stopCh, op.serviceInformer.HasSynced)
	cache.WaitForCacheSync(stopCh, op.endpointsInformer.HasSynced)
	glog.Info("Cache primed. Ready for operations.")

	for i := 0; i < threadiness; i++ {
		go wait.Until(op.runWorker, time.Second, stopCh)
	}

	ticker := time.NewTicker(SERVICE_RECHECK_INTERVAL)
	go func() {
		for {
			select {
			case <-ticker.C:
				glog.V(2).Infof("Next reconciliation check in %v", SERVICE_RECHECK_INTERVAL)
				op.queue.Add(true)
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

func (op *Operator) syncHandler(_ interface{}) error {
	store := op.serviceInformer.GetStore()
	attachedIPs, err := op.existingIPs()
	if err != nil {
		return err
	}
	externalIPs := map[string]bool{}
	for _, obj := range store.List() {
		svc := obj.(*v1.Service)
		if len(svc.Spec.ExternalIPs) == 0 {
			continue
		}
		if _, ok := svc.Annotations[IgnoreSvcAnnotation]; ok {
			glog.V(2).Infof("Skipping explicitly excluded svc %s", svc.Name)
			continue
		}
		obj, exits, err := op.endpointsInformer.GetStore().Get(svc)
		if !exits || err != nil {
			glog.Warningf("Skipping service %s, endpoints not found: %s", svc.Name, err)
			continue
		}
		endpoints := obj.(*v1.Endpoints)
		activeAddresses := 0
		for _, subset := range endpoints.Subsets {
			activeAddresses += len(subset.Addresses)
		}
		if activeAddresses == 0 {
			glog.V(2).Infof("Skipping service %s. No active endpoints", svc.Name)
			continue
		}
		for _, ip := range svc.Spec.ExternalIPs {
			externalIPs[ip] = true
		}
	}
	//add missing external ips to interface
	for ip, _ := range externalIPs {
		if _, ok := attachedIPs[ip]; !ok && !op.ignoreAddress(ip) {
			glog.Infof("Adding %s to interface %s", ip, op.NetworkInterface)
			_, err := exec.Command("ip", "addr", "add", ip, "dev", op.NetworkInterface).CombinedOutput()
			if err != nil {
				return err
			}
			if op.SourceAddress != "" {
				glog.Infof("Modifying local route for %s", ip)
				_, err = exec.Command("ip", "route", "change", "local", ip, "table", "local", "dev", op.NetworkInterface, "proto", "kernel", "scope", "host", "src", op.SourceAddress).CombinedOutput()
				if err != nil {
					return err
				}
			}
		}
	}

	//remove unaccounted ips from interface
	for ip, _ := range attachedIPs {
		if _, ok := externalIPs[ip]; !ok && !op.ignoreAddress(ip) {
			if err := op.removeIP(ip); err != nil {
				return err
			}
		}
	}
	return nil
}

func (op *Operator) ignoreAddress(ipstring string) bool {
	ip := net.ParseIP(ipstring)
	ip.String()
	if ip == nil {
		glog.V(3).Infof("Ignore invalid ip: %s", ipstring)
		return true
	}
	if ip.To4() == nil {
		glog.V(3).Infof("Ignore IPv6 ip: %s", ipstring)
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
	glog.Info("Added service with external IPs: ", svc.GetName())
	op.queue.Add(true)
}

func (op *Operator) serviceDelete(obj interface{}) {
	svc := obj.(*v1.Service)
	if len(svc.Spec.ExternalIPs) == 0 {
		return
	}
	glog.Info("Removed service with external IPs: ", svc.GetName())
	op.queue.Add(true)
}

func (op *Operator) serviceUpdate(cur, old interface{}) {
	curSvc := cur.(*v1.Service)
	oldSvc := old.(*v1.Service)

	annotationUnchanged := oldSvc.Annotations[IgnoreSvcAnnotation] == curSvc.Annotations[IgnoreSvcAnnotation]
	// No changes to externalIPs
	if reflect.DeepEqual(curSvc.Spec.ExternalIPs, oldSvc.Spec.ExternalIPs) && annotationUnchanged {
		return
	}
	glog.Info("External IP configuration change detected for service ", curSvc.GetName())
	op.queue.Add(true)
}

func (op *Operator) endpointsUpdate(cur, old interface{}) {
	oldEndpoints := old.(*v1.Endpoints)
	endpoints := cur.(*v1.Endpoints)

	//Nothing to do if subsets are unchanged
	if reflect.DeepEqual(oldEndpoints.Subsets, endpoints.Subsets) {
		return
	}

	//Get service for updated endpoints
	obj, exists, err := op.serviceInformer.GetStore().Get(endpoints)
	if !exists || err != nil {
		glog.Warningf("Can't find service for endpoints %s: %s", endpoints.GetName(), err)
		return
	}
	svc := obj.(*v1.Service)
	//Ignore services without external ips
	if len(svc.Spec.ExternalIPs) == 0 {
		return
	}
	glog.Infof("Endpoints changed for service %s", svc.GetName())
	op.queue.Add(true)
}

// WriteLine join all words with spaces, terminate with newline and write to buff.
func writeLine(buf *bytes.Buffer, words ...string) {
	// We avoid strings.Join for performance reasons.
	for i := range words {
		buf.WriteString(words[i])
		if i < len(words)-1 {
			buf.WriteByte(' ')
		} else {
			buf.WriteByte('\n')
		}
	}
}

func (op *Operator) removeIP(ip string) error {
	glog.Infof("Removing %s from interface %s", ip, op.NetworkInterface)
	out, err := exec.Command("ip", "addr", "del", ip, "dev", op.NetworkInterface).CombinedOutput()
	if err != nil {
		glog.Errorf("Error removing ip address %s: %s", ip, string(out))
		return err
	}
	if op.SourceAddress != "" {
		glog.Infof("Removing custom local route for %s from interface %s", ip, op.NetworkInterface)
		out, err := exec.Command("ip", "route", "del", "local", ip, "table", "local").CombinedOutput()
		if err != nil {
			glog.Warningf("Error deleting modified route: %s", string(out))
		}
	}
	return nil
}
