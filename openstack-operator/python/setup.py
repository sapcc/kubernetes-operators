from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.1.1',
    packages='.',
    install_requires=[
        'python-keystoneclient==3.15.0',
        'python-novaclient==10.1.0',
        'python-neutronclient==6.7.0',
        'python-designateclient==2.9.0',
        'python-swiftclient==3.5.0',
        'PyYAML==3.12',
        'raven',
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
