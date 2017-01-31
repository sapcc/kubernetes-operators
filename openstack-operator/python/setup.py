from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.0.1',
    packages='.',
    install_requires=[
        'PyYAML==3.12',
        'python-keystoneclient==3.8.0',
        'python-novaclient==7.0.0',
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
