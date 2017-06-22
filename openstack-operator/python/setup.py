from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.0.6',
    packages='.',
    install_requires=[
        'python-keystoneclient==3.10.0',
        'python-novaclient==9.0.0',
        'python-neutronclient==6.3.0',
        'python-designateclient==2.6.0',
        'python-swiftclient==3.3.0',
        'PyYAML==3.12',
    ],
    url='https://github.com/sapcc/kubernetes-operators/openstack-operator',
    license='',
    author='Rudolf Vriend',
    author_email='rudolf.vriend@sap.com',
    description='Openstack Seeder',
    entry_points = {
        "console_scripts": [
            'openstack-seeder = openstack_seeder:main',
        ]
        },
)
