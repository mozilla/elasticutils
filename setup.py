import os
import re
from setuptools import find_packages, setup


READMEFILE = "README.rst"
VERSIONFILE = os.path.join("elasticutils", "_version.py")
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"


def get_version():
    verstrline = open(VERSIONFILE, "rt").read()
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError(
            "Unable to find version string in %s." % VERSIONFILE)


setup(
    name='elasticutils',
    version=get_version(),
    description='Chainable interface to querying Elasticsearch',
    long_description=open(READMEFILE).read(),
    url='https://github.com/mozilla/elasticutils',
    author='Mozilla Foundation and contributors',
    license='BSD',
    packages=find_packages(),
    install_requires=[
        'elasticsearch>=0.4.3'
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Natural Language :: English',
        ],
)
