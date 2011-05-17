import sys

from setuptools import setup, find_packages

setup(
    name='elasticutils',
    version='0.1',
    description='Chainable interface to querying ElasticSearch',
    long_description=open('README').read(),
    author='Dave Dash',
    author_email='dd+pypi@davedash.com',
    license='BSD',
    packages=find_packages(),
    install_requires=['Nose', 'pyes'],
    include_package_data=True,
    classifiers = [
            'Development Status :: 4 - Beta',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Natural Language :: English',
        ]
)

