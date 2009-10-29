from setuptools import setup, find_packages
import sys, os

author, email = "Rune Halvorsen", "runefh@gmail.com"
version = 0.3.3
homepage = "http://bitbucket.org/runeh/tweetstream/"

setup(name='tweetstream',
    version=tweetstream.version
    description="Simple Twitter streaming API access",
    long_description=open("README").read(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
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
)
