#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='tweetstream',
    version='2.0-dev',
    description="Simple access to Twitter's streaming API",
    long_description=open('README.md').read(),
    packages=['tweetstream'],
    install_requires=['requests>=1.0.0,<=1.2.3'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    license='BSD',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ],
)
