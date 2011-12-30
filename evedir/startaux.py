#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import logging

import anzu.options
import anzu.web
from anzu.options import options

from evedir import uimodule
import evedir.option_definitions

__all__ = [
    'get_db', 'read_configuration_and_options', 'get_main_application',
]

def get_db(echo=False):
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    from sqlalchemy.exc import SAWarning
    from warnings import filterwarnings

    from evedir.model import DeclarativeBase

    # That conversion is done automatically. Therefore we can ignore the warning:
    filterwarnings('ignore', '^Unicode type received non-unicode bind param value', SAWarning)

    # This implicates a connection pool of 5 connections with 10 as permitted overflow; timeout of 30 seconds.
    # See also http://www.sqlalchemy.org/docs/06/core/engines.html#database-urls .
    engine = create_engine(
        options.database,
        echo=echo,
        pool_recycle=3600, # in case MySQL is used
    )

    # If tables already exist, then this will do no harm other than delaying start.
    # And, this will crete any missing tables.
    DeclarativeBase.metadata.create_all(engine)

    # This maps objects to database engines.
    bindings = dict(
        [(c, engine) for c in DeclarativeBase._decl_class_registry.values()]
    )
    return sessionmaker(binds=bindings)

def get_main_application(options):
    settings = {
        "static_path":                  os.path.join(os.path.dirname(__file__), "..", "static"),
        "template_path":                os.path.join(os.path.dirname(__file__), "templates"),
        "cookie_secret":                options.cookie_secret,
        "login_url":                    options.login_url,
        "xsrf_cookies":                 True,
        "debug":                        options.debug,
        "compress_whitespace":          options.compress_whitespace,
        "mako_module_directory":        options.mako_module_directory,
        "ui_modules":                   uimodule,
    }
    application = anzu.web.Application(**settings)
    application._db = get_db()
    return application

def read_configuration_and_options(machine_config = "/etc/evedir.conf"):
    anzu.options.parse_config_file("default.conf")
    try:
        anzu.options.parse_config_file(machine_config)
    except IOError:
        logging.info("%s was not found, running with defaults" % machine_config)
    anzu.options.parse_command_line()

    # check for vital options and their values:

    if not options.public_keyfile or not options.private_keyfile:
        logging.exception("You need to set filenames for public and private key.")
        sys.exit(3)
