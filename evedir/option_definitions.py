#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import urandom

from anzu.options import define

__all__ = []

define("port", default=8080, help="run on the given port", type=int)
define("debug", default=False, help="enables Anzu's debugging options", type=bool)
define("compress_whitespace", default=True, help="eliminates unnecessary whitespace within Mako's templates", type=bool)
define("cookie_secret", default=urandom(8192), help="seed and key for various cookie securing functions")
define("login_url", default="/login", help="where unauthenticated users shall be send to")

define("database", default="sqlite:////var/lib/evedir/data.sqlite3", help="the database connection string that will be passed to SQL-Alchemy")
define("hostname", help="public hostname (including http:// or https://) of this installation - without port")

define("file_storage", default="/var/lib/evedir", help="this directory will be used to store files related to capaigns")
