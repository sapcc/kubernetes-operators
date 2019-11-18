package metrics

import (
	"fmt"
	"github.com/prometheus/client_golang/prometheus"
	"net"
	"net/http"
	"sync"

	"github.com/go-kit/kit/log"
	"github.com/go-kit/kit/log/level"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const metricNamespace = ""

var (
	MetricErrorAssociateInstanceAndFIP = prometheus.NewCounter(prometheus.CounterOpts{
		Namespace: metricNamespace,
		Name: "associate_instance_fip_errors_total",
		Help: "Counter for associating instance and FIP errors.",
	})

	MetricErrorCreateFIP = prometheus.NewCounter(prometheus.CounterOpts{
		Namespace: metricNamespace,
		Name: "create_fip_errors_total",
		Help: "Counter for creating FIP errors.",
	})

	MetricSuccessfulOperations = prometheus.NewCounter(prometheus.CounterOpts{
		Namespace: metricNamespace,
		Name: "successful_operations_total",
		Help: "Counter for succcessful operations.",
	})
)

func init() {
	prometheus.MustRegister(
		MetricErrorAssociateInstanceAndFIP,
		MetricErrorCreateFIP,
		MetricSuccessfulOperations,
	)
}

// ServeMetrics starts the Prometheus metrics collector.
func ServeMetrics(host net.IP, port int, wg *sync.WaitGroup, stop <-chan struct{}, logger log.Logger) {
	wg.Add(1)
	defer wg.Done()

	logger = log.With(logger, "component", "metrics")

	addr := fmt.Sprintf("%s:%d", host.String(), port)
	l, err := net.Listen("tcp", addr)
	if err != nil {
		level.Error(logger).Log("msg", "failed serve prometheus metrics", "err", err)
		return
	}
	defer l.Close()
	level.Info(logger).Log("msg", "serving prometheus metrics", "address", addr, "path", "/metrics")

	go http.Serve(l, promhttp.Handler())
	<-stop
}
