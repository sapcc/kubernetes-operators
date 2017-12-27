import hashlib
import logging

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, contextfilter

from masterpassword import MasterPassword

LOG = logging.getLogger(__name__)


def _quote(value):
    return '"{}"'.format(_ini_escape(value).replace('"', '\\"'))


def _ini_escape(value):
    return str(value).replace('$', '$$')


@contextfilter
def _derive_password(ctx, username=None, host=None):
    username = username or ctx['username']
    host = host or ctx['host']
    mpw = MasterPassword(name=username, password=ctx['master_password'])
    password = mpw.derive('long', host).replace("/", "")

    if host.startswith('vc-'):
        return password.replace("/", "")

    return password


def _sha256sum(data):
    sha1 = hashlib.new('sha256')
    sha1.update(data)
    return sha1.hexdigest()


@contextfilter
def _render(ctx, template_name):
    template = ctx.environment.get_template(template_name)
    return template.render(ctx)


env = Environment(loader=ChoiceLoader([FileSystemLoader('/var/lib/kolla/config_files', followlinks=True),
                                       PackageLoader('vcenter_operator', 'templates')]))
env.filters['ini_escape'] = _ini_escape
env.filters['quote'] = _quote
env.filters['derive_password'] = _derive_password
env.filters['sha256sum'] = _sha256sum
env.filters['render'] = _render
