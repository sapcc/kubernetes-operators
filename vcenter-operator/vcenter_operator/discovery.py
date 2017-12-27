import logging
from collections import defaultdict

import attr
import six
from dns import tsigkeyring
from dns.query import xfr
from dns.rdatatype import SOA, A, AAAA, CNAME, AXFR
from kubernetes import client

log = logging.getLogger(__name__)


@attr.s
class _Callbacks(object):
    callbacks = attr.ib(default=attr.Factory(list))
    items = attr.ib(default=attr.Factory(set))
    accumulator = attr.ib(default=attr.Factory(set))


class DnsDiscovery(object):
    def __init__(self, domain, global_options):
        self._patterns = defaultdict(_Callbacks)

        self.domain = domain
        self.serial = None
        self.rdtype = AXFR
        self.keyname = 'tsig-key'

        self.keyring = None
        rndc_key = global_options.get('tsig_key', None)
        if rndc_key:
            self.keyring = tsigkeyring.from_text({self.keyname: rndc_key})

        self.namespace = global_options['namespace']
        token = client.configuration.auth_settings().get('BearerToken', None)
        self.cluster_internal = token and token['type'] == 'api_key' and not not token['value']
        self.ip = global_options.get('dns_ip', None)
        self.port = int(global_options.get('dns_port', 53))
        if not self.ip:
            self._discover_dns()

    def register(self, pattern, callback):
        self._patterns[pattern].callbacks.append(callback)

    def _discover_dns(self):
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
        for message in xfr(self.ip, self.domain, port=self.port, use_udp=False, rdtype=SOA, keyname=self.keyname,
                           keyring=self.keyring):
            for answer in message.answer:
                if answer.rdtype == SOA:
                    return answer[0].serial
        return None

    def discover(self):
        new_serial = self.remote_soa_serial()

        if self.serial and self.serial == new_serial:
            log.debug("No change of SOA serial")
            return

        for item in six.itervalues(self._patterns):
            item.accumulator = set()

        for message in xfr(self.ip, self.domain, port=self.port, use_udp=False, rdtype=self.rdtype,
                           keyname=self.keyname, keyring=self.keyring):
            for answer in message.answer:
                if answer.rdtype in [A, AAAA, CNAME] and answer.name:
                    for pattern, item in six.iteritems(self._patterns):
                        if pattern.match(answer.name.labels[0]):
                            item.accumulator.add(str(answer.name))

        for item in six.itervalues(self._patterns):
            log.debug("{}: {}".format(new_serial, item.accumulator))
            item.accumulator.difference_update(item.items)
            gone = item.items.difference(item.accumulator)
            for callback in item.callbacks:
                callback(item.accumulator, gone)

            item.items.update(item.accumulator)

        self.serial = new_serial
