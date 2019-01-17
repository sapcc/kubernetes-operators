from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.1.5',
    packages='.',
    install_requires=[
        'python-keystoneclient==3.18.0',
        'python-novaclient==11.1.0',
        'python-neutronclient==6.11.0',
        'python-designateclient==2.11.0',
        'python-swiftclient==3.6.0',
        'osc-placement==1.3.0',
        'raven',
        'pyyaml>=4.2b4',
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
