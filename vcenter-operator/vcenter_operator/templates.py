from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader('vcenter_operator', 'templates'))

