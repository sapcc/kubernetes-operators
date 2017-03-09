import logging, re, six
from time import sleep
from kubernetes import config as k8s_config
from .discovery import DnsDiscovery
from .configurator import Configurator

log = logging.getLogger(__name__)


def main():
    global_options = {}

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(message)s')
    logging.getLogger('kubernetes').setLevel(logging.WARNING)

    try:
        k8s_config.load_kube_config()
        _, context = k8s_config.list_kube_config_contexts()
        region = context['context']['cluster']
        domain = 'cc.{}.cloud.sap'.format(region)
        global_options['own_namespace'] = 'kube-system' #context['context']['namespace']
    except IOError:
        from os import environ
        environ['KUBERNETES_SERVICE_HOST'] = 'kubernetes.default'
        k8s_config.load_incluster_config()
        with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as f:
            global_options['own_namespace'] = f.read()
        with open('/etc/resolv.conf', 'r') as f:
            for l in f:
                if re.match('^search\s+', l):
                    _, domain = l.rsplit(' ', 1)
                    domain = domain.strip()

    configurator = Configurator(domain, global_options)
    configurator.poll_config()
    discovery = DnsDiscovery(domain, configurator.global_options)
    discovery.register(re.compile(six.b('\Avc-[a-z]+-?\d+\Z')), configurator)

    while True:
        discovery.discover()
        configurator.poll()
        sleep(10)
