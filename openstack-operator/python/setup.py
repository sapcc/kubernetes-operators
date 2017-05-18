from setuptools import setup

setup(
    name='openstack_seeder',
    version='0.0.5',
    packages='.',
    install_requires=[
        'openstacksdk==0.9.16',
        'python-openstackclient==3.11.0',
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
