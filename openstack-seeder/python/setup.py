from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.1.2',
    packages='.',
    install_requires=[
        'python-keystoneclient==3.17.0',
        'python-novaclient==11.0.0',
        'python-neutronclient==6.9.0',
        'python-designateclient==2.10.0',
        'python-swiftclient==3.6.0',
        'PyYAML==3.12',
        'raven',
    ],
    url='https://github.com/sapcc/kubernetes-operators/openstack-seeder',
    license='',
    author='Rudolf Vriend',
    author_email='rudolf.vriend@sap.com',
    description='Openstack Seeder',
    entry_points = {
        "console_scripts": [
            'openstack-seed-loader = openstack_seeder:main',
        ]
        },
)
