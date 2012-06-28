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
    description='Chainable interface to querying ElasticSearch',
    long_description=open(READMEFILE).read(),
    url='https://github.com/mozilla/elasticutils',
    author='Mozilla Foundation and contributors',
    license='BSD',
    packages=find_packages(),
    install_requires=['pyes>=0.15,<0.17'],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Natural Language :: English',
        ],
)
