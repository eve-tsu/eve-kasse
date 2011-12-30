#!/usr/bin/env python
# -*- coding: utf-8 -*-

import anzu.options
from anzu.options import options

import evedir.option_definitions
from evedir.model import User
from evedir.startaux import get_db, read_configuration_and_options

def create_administrator():
    default_admin_name = 'Tsu'
    default_admin_email = 'tsu@eve-economics.com'
    default_timezone = 'Europe/Berlin'

    administrator = User(
        name = raw_input("admin name [%s]: " % default_admin_name) or default_admin_name,
        email_address = raw_input("admin email address [%s]: " % default_admin_email) or default_admin_email,
        timezone = raw_input("timezone [%s]: " % default_timezone) or default_timezone,
        password = raw_input("admin password (will be shown here!): "),
    )
    return administrator

def main():
    read_configuration_and_options()
    Session = get_db()
    session = Session()

    if (raw_input("\nCreate Administrator? [Y/n]: ") or 'y') in ['Y', 'y']:
        session.add(create_administrator())
        session.commit()

if __name__ == "__main__":
    main()
