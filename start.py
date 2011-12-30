#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 W-Mark Kubacki; wmark@hurrikane.de
#

import anzu.httpserver
import anzu.ioloop
import anzu.locale
import anzu.options
from anzu.options import options, enable_pretty_logging

import evedir.option_definitions
from evedir.controller import uac, dashboard
from evedir.startaux import get_main_application, read_configuration_and_options
from evedir.jobs import Process
from evedir.jobs.wallet import wallet_synchronization

__all__ = ['main', ]

def main():
    enable_pretty_logging()
    read_configuration_and_options()

    # here the webserver gets created
    application = get_main_application(options=options)
    http_server = anzu.httpserver.HTTPServer(application, xheaders=True)
    http_server.listen(options.port)

    # (threads and co-processes get started here)
    processes = []
    p = Process(target=wallet_synchronization, args=(application._db, ))
    p.start()
    processes.append(p)

    # ... and started
    try:
        anzu.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

    # end all threads or coprocesses
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()

if __name__ == "__main__":
    main()
