from setuptools import setup

setup(
    name='keystone_seeder',
    version='0.0.1',
    packages='.',
    install_requires=[
        'PyYAML==3.12',
        'python-keystoneclient==3.8.0',
    ],
    url='https://github.com/sapcc/kubernetes-operators/keystone-operator',
    license='',
    author='Rudolf Vriend',
    author_email='rudolf.vriend@sap.com',
    description='Keystone Seeder',
    entry_points = {
        "console_scripts": [
            'keystone-seeder = keystone_seeder:main',
        ]
        },
)
