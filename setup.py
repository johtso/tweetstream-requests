try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

import sys, os

author = "Rune Halvorsen" 
email = "runefh@gmail.com"
version = "1.1.0"
homepage = "http://bitbucket.org/runeh/tweetstream/"

extra = {}
if sys.version_info >= (3, 0):
    extra.update(use_2to3=True)




setup(name='tweetstream',
    version=version,
    description="Simple Twitter streaming API access",
    long_description=open("README").read(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
    ],
    keywords='twitter',
    author=author,
    author_email=email,
    url=homepage,
    license='BSD',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    platforms=["any"],
    install_requires = ['anyjson'],
    **extra
)
