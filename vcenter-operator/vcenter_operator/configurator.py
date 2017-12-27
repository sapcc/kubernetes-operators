import atexit
import logging
import re
import ssl
import sys
from collections import defaultdict, deque
from contextlib import contextmanager
from os.path import commonprefix
from socket import error as socket_error

import six
from kubernetes import client
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from .masterpassword import MasterPassword
from .phelm import DeploymentState
from .templates import env
from .vcenter_util import *

LOG = logging.getLogger(__name__)


@contextmanager
def filter_spec_context(service_instance):
    try:
        obj_type = vim.ClusterComputeResource
        view_ref = get_container_view(service_instance, obj_type=[obj_type])
        yield create_filter_spec(view_ref=view_ref,
                                 obj_type=obj_type,
                                 path_set=['name', 'parent', 'datastore', 'network'])
    finally:
        view_ref.DestroyView()


class Configurator(object):
    CLUSTER_MATCH = re.compile('^production(bb[1-9][0-9]*)$')
    EPH_MATCH = re.compile('^eph.*$')
    BR_MATCH = re.compile('^br-(.*)$')

    def __init__(self, domain, global_options={}):
        self.global_options = global_options.copy()
        self.password = None
        self.mpw = None
        self.domain = domain
        self.vcenters = dict()
        self.clusters = defaultdict(dict)
        self.states = deque()
        self.poll_config()

    def __call__(self, added, removed):
        for name in added:
            try:
                host = '{}.{}'.format(name, self.domain)
                if host in self.vcenters:
                    continue

                password = self.mpw.derive('long', host).replace("/", "")  # Vcenter doesn't accept / in password

                LOG.info("{}".format(host))
                if hasattr(ssl, '_create_unverified_context'):
                    context = ssl._create_unverified_context()

                    service_instance = SmartConnect(host=host,
                                                    user=self.username,
                                                    pwd=password,
                                                    port=443,
                                                    sslContext=context)

                if service_instance:
                    atexit.register(Disconnect, service_instance)

                    self.vcenters[host] = {'service_instance': service_instance,
                                           'username': self.username,
                                           'password': password,
                                           'host': host,
                                           'name': name,
                                           }

            except vim.fault.InvalidLogin as e:
                LOG.error("%s: %s", host, e.msg)
            except socket_error as e:
                LOG.error("%s: %s", host, e)

        if removed:
            LOG.info("Gone vcs {}".format(removed))

    def _poll(self, host):
        vcenter_options = self.vcenters[host]
        service_instance = vcenter_options['service_instance']
        with filter_spec_context(service_instance) as filter_spec:
            availability_zones = set()

            for cluster in collect_properties(service_instance, [filter_spec]):
                cluster_name = cluster['name']
                match = self.CLUSTER_MATCH.match(cluster_name)

                if not match:
                    LOG.debug("%s: Ignoring cluster %s not matching naming scheme", host, cluster_name)
                    continue

                parent = cluster['parent']
                availability_zone = parent.parent.name.lower()
                availability_zones.add(availability_zone)
                cluster_options = self.global_options.copy()
                cluster_options.update(vcenter_options)
                cluster_options.update(name=match.group(1).lower(),
                                       cluster_name=cluster_name,
                                       availability_zone=availability_zone)

                if cluster_options.get('pbm_enabled', 'false') != 'true':
                    datastores = cluster['datastore']
                    datastore_names = [datastore.name for datastore in datastores if
                                       self.EPH_MATCH.match(datastore.name)]
                    eph = commonprefix(datastore_names)
                    cluster_options.update(datastore_regex="^{}.*".format(eph))

                for network in cluster['network']:
                    match = self.BR_MATCH.match(network.name)
                    if match:
                        cluster_options['bridge'] = match.group(0).lower()
                        cluster_options['physical'] = match.group(1).lower()
                        break

                if not 'bridge' in cluster_options:
                    LOG.warning("%s: Skipping cluster %s, cannot find bridge matching naming scheme", host,
                                cluster_name)
                    continue

                cluster_state = self.clusters[cluster_name]
                config_hash = hash(frozenset(cluster_options.items()))
                cluster_options['config_hash'] = config_hash + sys.maxsize
                cluster_state['config_hash'] = config_hash
                self._add_code('vcenter_cluster', cluster_options)

            for availability_zone in availability_zones:
                cluster_options = self.global_options.copy()
                cluster_options.update(vcenter_options)
                cluster_options.update(availability_zone=availability_zone)

            self._add_code('vcenter_datacenter', cluster_options)

    def _add_code(self, scope, options):
        for template_name in env.list_templates(filter_func=lambda x: x.startswith(scope) and x.endswith('.yaml.j2')):
            template = env.get_template(template_name)
            result = template.render(options)
            self.states[-1].add(result)

    @property
    def _client(self):
        return client

    @property
    def username(self):
        return self.global_options['username']

    @property
    def namespace(self):
        return self.global_options['own_namespace']

    def poll_config(self):
        configmap = client.CoreV1Api().read_namespaced_config_map(namespace=self.namespace,
                                                                  name='vcenter-operator',
                                                                  export=True)
        password = configmap.data.pop('password')
        self.global_options.update(configmap.data)
        if self.password != password:
            self.global_options.update(master_password=password)
            self.password = password
            self.mpw = MasterPassword(self.username, self.password)

    def poll(self):
        self.poll_config()
        self.states.append(DeploymentState(namespace=self.global_options['namespace'],
                                           dry_run=(self.global_options.get('dry_run', 'False') == 'True')))
        self._add_code('global', self.global_options)

        for host in six.iterkeys(self.vcenters):
            try:
                self._poll(host)
            except six.moves.http_client.HTTPException as e:
                LOG.warning("%s: %r", host, e)
                continue

        if len(self.states) > 1:
            last = self.states.popleft()
            delta = last.delta(self.states[-1])
            delta.apply()
        else:
            self.states[-1].apply()
