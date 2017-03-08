import logging, re, six
from dns.query import xfr
from dns.rdatatype import SOA, A, AAAA, CNAME, AXFR, IXFR
from kubernetes import client

log = logging.getLogger(__name__)


class DnsDiscovery(object):
    VC_MATCH = re.compile(six.b('\Avc-[a-z]+-?\d+\Z'))

    def __init__(self, domain, global_options):
        self.ip = None
        self.namespace = global_options['namespace']
        self.domain = domain
        self.all_vcs = set()
        self.rdtype = AXFR
        self.serial = None
        token = client.configuration.auth_settings().get('BearerToken', None)
        self.cluster_internal = token and token['type'] == 'api_key' and not not token['value']
        self._init_dns()

    def _init_dns(self):
        for item in client.CoreV1Api().list_namespaced_service(namespace=self.namespace,
                                                               label_selector='component=designate,type=backend').items:
            spec = item.spec
            for port in spec.ports:
                if self.cluster_internal:
                    self.ip = spec.cluster_ip
                    self.port = port.target_port
                    return
                elif spec.external_i_ps:
                    self.ip = spec.external_i_ps[0]
                    self.port = port.port
                    return

    def remote_soa_serial(self):
        for message in xfr(self.ip, self.domain, port=self.port, use_udp=False, rdtype=SOA):
            for answer in message.answer:
                if answer.rdtype==SOA:
                    return answer[0].serial
        return None

    def discover(self, changes):
        vcs = set()

        new_serial = self.remote_soa_serial()

        if self.serial and self.serial == new_serial:
            log.debug("No change of SOA serial")
            return

        for message in xfr(self.ip, self.domain, port=self.port, use_udp=False, rdtype=self.rdtype):
            for answer in message.answer:
                if answer.rdtype in [A, AAAA, CNAME] and answer.name:
                    if self.VC_MATCH.match(answer.name.labels[0]):
                        vc = str(answer.name)
                        if not vc in vcs:
                            vcs.add(vc)

        log.debug("{}: {}".format(new_serial, vcs))
        vcs.difference_update(self.all_vcs)
        gone = self.all_vcs.difference(vcs)
        changes(vcs, gone)

        self.all_vcs.update(vcs)
        self.serial = new_serial