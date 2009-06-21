from setuptools import setup, find_packages
import sys, os

import tweetstream
author, email = tweetstream.__author__[:-1].split(' <')

setup(name='tweetstream',
    version=tweetstream.__version__,
    description="Simple Twitter streaming API access",
    long_description=open("README").read(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
    ],
    keywords='twitter',
    author=author,
    author_email=email,
    url=tweetstream.__homepage__,
    license='BSD',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    platforms=["any"],
)
