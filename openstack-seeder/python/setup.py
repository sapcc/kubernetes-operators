from setuptools import setup

setup(
    name='openstack_seeder',
    version='2.0.1',
    packages='.',
    install_requires=[
        'python-keystoneclient>=3.20.0',
        'python-novaclient>=14.2.0',
        'python-neutronclient>=6.12.0',
        'python-designateclient>=2.11.0',
        'python-swiftclient>=3.8.0',
        'python-manilaclient>=1.27.0',
        'python-cinderclient>=6.0.0',
        'osc-placement>=1.4.0',
        'raven',
        'zipp==3.19.2',
        'pyyaml>=4.2b4',
        'pyparsing==2.1.0',
        'oslo.serialization==2.29.2',
        'funcsigs',
        'oslo.config==7.0.0',
        'python-dateutil>=2.7.0',
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
