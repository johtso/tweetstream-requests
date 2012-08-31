import sys
import os

# extra = {}
# if sys.version_info >= (3, 0):
#     extra.update(use_2to3=True)


try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


# -*- Distribution Meta -*-
import re
re_meta = re.compile(r'__(\w+?)__\s*=\s*(.*)')
re_vers = re.compile(r'VERSION\s*=\s*\((.*?)\)')
re_doc = re.compile(r'^"""(.+?)"""', re.M|re.S)
rq = lambda s: s.strip("\"'")


def add_default(m):
    attr_name, attr_value = m.groups()
    return ((attr_name, rq(attr_value)), )


def add_version(m):
    v = list(map(rq, m.groups()[0].split(", ")))
    return (("VERSION", ".".join(v[0:3]) + "".join(v[3:])), )


def add_doc(m):
    return (("doc", m.groups()[0].replace("\n", " ")), )

pats = {re_meta: add_default,
        re_vers: add_version}
here = os.path.abspath(os.path.dirname(__file__))
meta_fh = open(os.path.join(here, "tweetstream/__init__.py"))
try:
    meta = {}
    acc = []
    for line in meta_fh:
        if line.strip() == '# -eof meta-':
            break
        acc.append(line)
        for pattern, handler in pats.items():
            m = pattern.match(line.strip())
            if m:
                meta.update(handler(m))
    m = re_doc.match("".join(acc).strip())
    if m:
        meta.update(add_doc(m))
finally:
    meta_fh.close()


setup(name='tweetstream',
    version=meta["VERSION"],
    description=meta["doc"],
    long_description=open("README").read(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.1',
    ],
    keywords='twitter',
    author=meta["author"],
    author_email=meta["contact"],
    url=meta["homepage"],
    license='BSD',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    platforms=["any"],
    install_requires=['anyjson']
#    **extra
)
