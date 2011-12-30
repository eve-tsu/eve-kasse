#!/usr/bin/env python
#
# Copyright 2011 W-Mark Kubacki; wmark@hurrikane.de

import distutils.core
import sys
from os import walk
from os.path import join, dirname
# Importing setuptools adds some features like "setup.py develop", but
# it's optional so swallow the error if it's not there.
try:
    import setuptools
except ImportError:
    pass

def find_data_files(path, prefix):
    lst = []
    for dirpath, dirnames, filenames in walk(path):
        lst.append((prefix + dirpath.replace(path, ''),
                    [dirpath+'/'+f for f in filenames]))
    return lst

# require Python 2.7 or later
major, minor = sys.version_info[:2]
python_27 = (major > 2 or (major == 2 and minor >= 7))
if not python_27:
    sys.exit(1)

from evedir import version

distutils.core.setup(
    name="EVE Direktor Assistant",
    version=version,

    packages = ["evedir",
                "evedir.controller",
    ],
    package_data = {
        'evedir': [t[10:] for t in (find_data_files('evedir/templates', 'templates')[0][1])],
    },
    data_files = find_data_files('static', 'static'),
    zip_safe = False,

    entry_points = {
        'console_scripts': [
            'evedir-start = start:main',
            'evedir-initialization = initialize:main',
#            'evedir-shell = shell:main',
        ],
    },

    author="W-Mark Kubacki",
    author_email="wmark@hurrikane.de",
    url="https://github.com/wmark/evedir",
    description="Manager of members and theirs skills; assets, walltets and campaigns.",
    install_requires = [
        "Anzu >= 1.2.1",
        "Mako >= 0.4.1",
        "sqlalchemy >= 0.6.7",
        "FormEncode >= 1.2.4",
        "python-dateutil >= 1.5",
        "pytz >= 2011e",
        "redis >= 2.0.0",
    ],
)
