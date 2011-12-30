#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import urandom
from hashlib import sha1
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, synonym
#from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, BigInteger, Numeric, \
#                       String, Text, Unicode, UniqueConstraint
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Unicode

DeclarativeBase = declarative_base()

__all__ = [
    'DeclarativeBase', 'User',
]

class User(DeclarativeBase):
    """
    Represents an known or registered person.
    """
    __tablename__ = 'users'

    id                  = Column('user', Integer, autoincrement=True, primary_key=True)
    name                = Column(Unicode(16), unique=True, nullable=False)
    email_address       = Column('email', Unicode(64), unique=True, index=True, nullable=False)
    timezone            = Column('timezone', Unicode(32), default=u'Europe/Berlin', nullable=False)
    _password           = Column('password', String(80))
    created             = Column(DateTime, default=datetime.utcnow)
    enabled             = Column(Boolean, nullable=False, default=True)

    # FK
    campaigns           = relationship("Campaign", order_by="Campaign.created.asc()", backref="creator")

    def _set_password(self, password):
        """Hash ``password`` on the fly and store its hashed version."""
        if isinstance(password, unicode):
            password_8bit = password.encode('UTF-8')
        else:
            password_8bit = password

        salt = sha1()
        salt.update(urandom(60))
        hash = sha1()
        hash.update(password_8bit + salt.hexdigest())
        hashed_password = salt.hexdigest() + hash.hexdigest()

        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('UTF-8')

        self._password = hashed_password

    def _get_password(self):
        """Return the hashed version of the password."""
        return self._password

    password = synonym('_password', descriptor=property(_get_password, _set_password))

    def validate_password(self, password):
        hashed_pass = sha1()
        hashed_pass.update(password + self.password[:40])
        return self.password[40:] == hashed_pass.hexdigest()


class Campaign(DeclarativeBase):
    """
    Represents an email campaign.
    """
    __tablename__ = 'campaigns'

    id                  = Column('campaign', Integer, autoincrement=True, primary_key=True)
    title               = Column(Unicode(64), unique=True, nullable=False)
    created             = Column('created', DateTime, default=datetime.utcnow)
    user_id             = Column('user', Integer, ForeignKey('users.user', onupdate='CASCADE', ondelete='RESTRICT'))
    collect_clickdata   = Column(Boolean, nullable=False, default=False)
    archived            = Column(Boolean, nullable=False, default=False)
    merger_file         = Column(Unicode(128), nullable=True)
    ingress_address     = Column('ingress_address', Unicode(96), unique=True, index=True, nullable=True)
    egress_address      = Column('egress_address', Unicode(96), index=True, nullable=True)

    no_recipients       = Column(Integer, nullable=True)
    no_unsubscriptions  = Column(Integer, nullable=False, default=0)


def test_create_tables():
    """Creates the tables in a SQLite3 database for testing purposes."""
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///test.db', echo=True)
    DeclarativeBase.metadata.create_all(engine)
