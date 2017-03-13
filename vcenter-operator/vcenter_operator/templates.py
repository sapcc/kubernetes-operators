from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader


def _quote(value):
    return '"{}"'.format(_ini_escape(value).replace('"', '\\"'))

def _ini_escape(value):
    return str(value).replace('$', '$$')

env = Environment(loader=ChoiceLoader([FileSystemLoader('/var/lib/kolla/config_files', followlinks=True), PackageLoader('vcenter_operator', 'templates')]))
env.filters['ini_escape'] = _ini_escape
env.filters['quote'] = _quote
