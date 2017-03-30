from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.0.2',
    packages='.',
    install_requires=[
        'requests==2.12.5',
        'python-openstackclient==3.2.1',
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
