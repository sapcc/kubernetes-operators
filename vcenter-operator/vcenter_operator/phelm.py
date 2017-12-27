import attr
import logging
import re
import six
import sys
import yaml
from kubernetes import client

log = logging.getLogger(__name__)


def _remove_empty_from_dict(d):
    if type(d) is dict:
        return dict((k, _remove_empty_from_dict(v)) for k, v in d.iteritems() if v and _remove_empty_from_dict(v))
    elif type(d) is list:
        return [_remove_empty_from_dict(v) for v in d if v and _remove_empty_from_dict(v)]
    else:
        return d


def _under_score(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


@attr.s
class DeploymentState(object):
    namespace = attr.ib()
    dry_run = attr.ib(default=False)
    items = attr.ib(default=attr.Factory(dict))
    actions = attr.ib(default=attr.Factory(dict))

    def add(self, result):
        stream = six.StringIO(result)
        for item in yaml.safe_load_all(stream):
            id = (item['apiVersion'], item['kind'], item['metadata']['name'])
            if id in self.items:
                log.warning("Duplicate item #{}".format(id))
            api = [p.capitalize() for p in id[0].split('/', 1)]
            klass = getattr(client, "".join([api[-1], id[1]]))
            api_client = client.ApiClient()
            self.items[id] = api_client._ApiClient__deserialize_model(item, klass)

    def delta(self, other):
        delta = DeploymentState(namespace=self.namespace)
        for k in six.viewkeys(self.items) - six.viewkeys(other.items):
            delta.actions[k] = 'delete'
        for k in six.viewkeys(self.items) & six.viewkeys(other.items):
            if self.items[k] != other.items[k]:
                delta.actions[k] = 'update'
                delta.items[k] = other.items[k]
            # Nothing to do otherwise
        for k in six.viewkeys(other.items) - six.viewkeys(self.items):
            delta.items[k] = other.items[k]

        return delta

    def _diff(self, old_item, new_item, level=0):
        if not new_item:
            return False
        if not old_item and new_item:
            return True

        for key in six.iterkeys(new_item.attribute_map):
            if 0 == level and key in ['status', 'kind']:
                continue
            if 1 == level and key in ['self_link']:
                continue

            old_value = getattr(old_item, key, None)
            new_value = getattr(new_item, key, None)

            if not new_value:
                continue

            if getattr(new_value, 'attribute_map', None):
                if self._diff(new_value, old_value, level + 1):
                    return True
            elif old_value != new_value:
                # log.debug("{} {}: {} <> {}".format(level, key, old_item, new_item))
                return key

        return False

    def _apply_delta(self, api, old_item, new_item):
        if self._diff(old_item, new_item):
            if not old_item:
                action = 'create'
                args = [self.namespace, new_item]
            else:
                action = 'patch'
                args = [new_item.metadata.name, self.namespace, new_item]

            underscored = _under_score(new_item.kind)

            if self.dry_run:
                log.info("{}: {}/{}".format(action.title(), underscored, new_item.metadata.name))
                for line in yaml.dump(_remove_empty_from_dict(new_item.to_dict())).split("\n"):
                    log.debug(line)
            else:
                log.debug("{}: {}/{}".format(action.title(), underscored, new_item.metadata.name))
                method = getattr(api, '{}_namespaced_{}'.format(action, underscored))
                method(*args)

    def get_api(self, api_version):
        api = [p.capitalize() for p in api_version.split('/', 1)]

        if len(api) == 1:
            api.insert(0, 'Core')

        return getattr(client, '{}{}Api'.format(api[0], api[1]), None)()

    @staticmethod
    def get_method(api, *items):
        return getattr(api, '_'.join(items))

    def apply(self):
        for (api_version, kind, name), target in six.iteritems(self.items):
            api = self.get_api(api_version)
            current = None
            try:
                reader = self.get_method(api, 'read', 'namespaced', _under_score(kind))
                current = reader(name, self.namespace, pretty=False, export=True)
            except client.rest.ApiException as e:
                if e.status == 404:
                    pass
                else:
                    six.reraise(*sys.exc_info())

            self._apply_delta(api, current, target)

        for (api_version, kind, name), action in six.iteritems(self.actions):
            if action != 'delete':
                continue

            api = self.get_api(api_version)
            underscored = _under_score(kind)
            if self.dry_run:
                log.info("{}: {}/{}".format(action.title(), underscored, name))
            else:
                try:
                    log.debug("{}: {}/{}".format(action.title(), underscored, name))
                    deleter = self.get_method(api, 'delete', 'namespaced', underscored)
                    deleter(name, self.namespace, client.V1DeleteOptions(orphan_dependents=False))
                except client.rest.ApiException as e:
                    if e.status == 404:
                        pass
                    else:
                        six.reraise(*sys.exc_info())
