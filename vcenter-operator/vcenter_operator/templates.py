from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader

env = Environment(loader=ChoiceLoader([FileSystemLoader('/var/lib/kolla/config_files', followlinks=True), PackageLoader('vcenter_operator', 'templates')]))


