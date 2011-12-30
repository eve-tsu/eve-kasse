#!/usr/bin/ipython -i
# -*- coding: utf-8 -*-

import anzu.options
from anzu.options import options

import evedir.option_definitions
from evedir.model import *
from evedir.startaux import get_db, read_configuration_and_options

# for our convenience only
from pytz import UTC
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import exc, or_, and_, func

if __name__ == "__main__":
    read_configuration_and_options()
    options.debug = True
    Session = get_db(echo=True)
    db = session = Session()
