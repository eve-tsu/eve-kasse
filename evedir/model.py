#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import urandom
from hashlib import sha1
from codecs import unicode_escape_decode
from datetime import datetime
import logging

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, synonym
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, Integer, Index, Numeric, \
                       String, Unicode, UniqueConstraint

DeclarativeBase = declarative_base()

__all__ = [
    'DeclarativeBase', 'User', 'Keypair', 'Toon', 'Corporation',
    'ACCOUNT_KEYS', 'WalletJournalEntry', 'WalletTransaction',
    'DefaultItemTag', 'WalletTag',
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
    keypairs            = relationship("Keypair", order_by="Keypair.announced.desc()", backref="holder")
    toons               = relationship("Toon", order_by="Toon.name.asc()", backref="holder")
    default_tags        = relationship("DefaultItemTag", order_by="DefaultItemTag.tagname.asc()", backref="user")
    wallet_tags         = relationship("WalletTag", order_by="WalletTag.tagname.asc()", backref="user")

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


class Keypair(DeclarativeBase):
    """
    Represents a EVE online API keypair.
    """
    __tablename__ = 'keypairs'

    keyID               = Column('keyid', BigInteger, primary_key=True)
    vCode               = Column(Unicode(128), nullable=False)
    accessMask          = Column('access_mask', BigInteger, nullable=False)
    type                = Column('key_type', Enum('Account', 'Character', 'Corporation'), nullable=False)
    corporationID       = Column('key_corporation', BigInteger, # for corporation keys, else NULL
                                 ForeignKey('corporations.corporationID', onupdate='CASCADE', ondelete='CASCADE'),
                                 index=True, nullable=True)
    characterID         = Column('key_character', BigInteger, # for corporation keys, else NULL
                                 ForeignKey('characters.character', onupdate='CASCADE'),
                                 nullable=True)
    announced           = Column(DateTime, default=datetime.utcnow)
    expires             = Column(DateTime, nullable=True)
    valid               = Column(Boolean, default=True, nullable=False)
    user_id             = Column('user', Integer, ForeignKey('users.user', onupdate='CASCADE', ondelete='RESTRICT'),
                                 nullable=False)

    # Constants
    ACCESS = {
        'Corporation': {
            'WalletJournal': 1048576,
            'WalletTransactions': 2097152,
        },
        'Character': {
            'WalletJournal': 2097152,
            'WalletTransactions': 4194304,
        }
    }
    ACCESS['Account'] = ACCESS['Character']

    def grants_access_to(self, section):
        if self.type in Keypair.ACCESS and section in Keypair.ACCESS[self.type] \
           and self.accessMask & Keypair.ACCESS[self.type][section]:
            return True
        else:
            return False


class Toon(DeclarativeBase):
    """
    An EVE online character. An account can have up to three.
    """
    __tablename__ = 'characters'

    characterID         = Column('character', BigInteger, primary_key=True)
    name                = Column('toon_name', Unicode(64), nullable=False)
    corporation_id      = Column('corporationID', BigInteger,
                                 ForeignKey('corporations.corporationID', onupdate='CASCADE', ondelete='RESTRICT'),
                                 nullable=False, index=True)
    user_id             = Column('user', Integer, ForeignKey('users.user', onupdate='CASCADE', ondelete='RESTRICT'),
                                 nullable=False, index=True)

    # collections
    wallet_journal_entries  = relationship("WalletJournalEntry", order_by="WalletJournalEntry.datetime.desc()", backref="toon")
    wallet_transactions     = relationship("WalletTransaction", order_by="WalletTransaction.transactionDateTime.desc()", backref="toon")


class Corporation(DeclarativeBase):
    """
    EVE online corporation. Can be an player-run or a NPC corporation.
    """
    __tablename__ = 'corporations'

    corporationID       = Column('corporationID', BigInteger, primary_key=True)
    name                = Column('corp_name', Unicode(128), nullable=False)

    # collections
    toons               = relationship("Toon", order_by="Toon.name.asc()", backref="corporation")
    corporation_keys    = relationship("Keypair", order_by="Keypair.accessMask.desc()", backref="corporation")
    wallet_journal_entries  = relationship("WalletJournalEntry", order_by="WalletJournalEntry.datetime.desc()", backref="corporation")
    wallet_transactions     = relationship("WalletTransaction", order_by="WalletTransaction.transactionDateTime.desc()",
                                           backref="corporation")
    default_tags        = relationship("DefaultItemTag", order_by="DefaultItemTag.tagname.asc()", backref="corporation")
    wallet_tags         = relationship("WalletTag", order_by="WalletTag.tagname.asc()", backref="corporation")


ACCOUNT_KEYS = ['1000', '1001', '1002', '1003', '1004', '1005', '1006']

class WalletJournalEntry(DeclarativeBase):
    """
    The journal contains items such as transactions sums, tax, fees, bounties, player tradings etc.
    """
    __tablename__ = 'wallet_journal'
#    __table_args__ = (
#        UniqueConstraint('datetime', 'ownerID1', 'ownerID2', 'RefTypeID',),
#    )
    __conversions__ = {
        'date': ('datetime', lambda v: datetime.fromtimestamp(v)),
        'reason': ('reason', lambda v: WalletJournalEntry.fix_reason_field(v)),
    }

    refID               = Column(BigInteger, primary_key=True)
    accountKey          = Column(Enum(*ACCOUNT_KEYS), default=ACCOUNT_KEYS[0], nullable=False)
    corporation_id      = Column('corporationID', BigInteger,
                                 ForeignKey('corporations.corporationID', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)
    character_id        = Column('character', BigInteger,
                                 ForeignKey('characters.character', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)

    datetime            = Column(DateTime, nullable=False, index=True)
    refTypeID           = Column(Integer, nullable=False) # e.g. 85=bounty tax, 97=PI tax 33=Mission Reward tax, 34=Mission time bonus tax
    ownerName1          = Column(Unicode(128), nullable=False)
    ownerID1            = Column(BigInteger, nullable=False)
    ownerName2          = Column(Unicode(128), nullable=False)
    ownerID2            = Column(BigInteger, nullable=False)
    argName1            = Column(Unicode(128), nullable=True) # 'transaction' if 'RefTypeID'==2
    argID1              = Column(Integer, nullable=False)
    amount              = Column(Numeric(precision=2, scale=2+9))
    balance             = Column(Numeric(precision=2, scale=2+12), nullable=True)
    reason              = Column(Unicode(128), nullable=True)
    taxReceiverID       = Column(BigInteger, nullable=True)
    taxAmount           = Column(Numeric(precision=2, scale=2+9), nullable=True)

    # FK
    tag_id              = Column('tag', Integer,
                                 ForeignKey('wallet_tag.tag', onupdate='CASCADE', ondelete='SET NULL'),
                                 nullable=True, index=True)

    @classmethod
    def bulk_insert(cls, rows, **common_values):
        return bulk_insert_into(cls, rows, **common_values)

    @classmethod
    def fix_reason_field(cls, reason):
        if not reason:
            return reason
        reason = reason.strip()
        if reason.startswith(u'DESC: "') and reason.endswith(u'"'):
            reason = u'DESC: '+reason[7:-1]
        # see https://forums.eveonline.com/default.aspx?g=posts&t=53350
        reason = unicode_escape_decode(reason)[0]
        return reason


class WalletTransaction(DeclarativeBase):
    """
    Transactions contain informations such as 'who' has given 'whom' 'how many' of 'what'.
    """
    __tablename__ = 'wallet_transactions'
    __table_args__ = (
        Index('stationID', 'transactionType'),
        Index('typeID', 'transactionType'),
    )
    __conversions__ = {
        'transactionID': ('transaction', ),
        'transactionDateTime': ('datetime', lambda v: datetime.fromtimestamp(v)),
        'characterID': ('executorID', ),
        'characterName': ('executorName', ),
    }

    transactionID       = Column('transaction', BigInteger, primary_key=True)
    accountKey          = Column(Enum(*ACCOUNT_KEYS), default=ACCOUNT_KEYS[0], nullable=False)
    corporation_id      = Column('corporationID', BigInteger,
                                 ForeignKey('corporations.corporationID', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)
    character_id        = Column('character', BigInteger,
                                 ForeignKey('characters.character', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)

    transactionDateTime = Column('datetime', DateTime, nullable=False, index=True)
    quantity            = Column(Integer, nullable=False)
    typeName            = Column(Unicode(128), nullable=True)
    typeID              = Column(BigInteger, nullable=False)
    price               = Column(Numeric(precision=2, scale=2+12), nullable=False)
    clientID            = Column(BigInteger, nullable=False)
    clientName          = Column(Unicode(128), nullable=False)
    stationID           = Column(Integer, nullable=False)
    stationName         = Column(Unicode(128), nullable=False)
    transactionType     = Column(Enum('buy', 'sell'), nullable=False)
    transactionFor      = Column(Enum('personal', 'corporation'), nullable=False)
    executorID          = Column(BigInteger, nullable=False)
    executorName        = Column(Unicode(64), nullable=False)
    journalTransactionID = Column(BigInteger,
                                 ForeignKey('wallet_journal.refID', onupdate='CASCADE', ondelete='SET NULL'),
                                 nullable=True, index=True)

    # FK
    tag_id              = Column('tag', Integer,
                                 ForeignKey('wallet_tag.tag', onupdate='CASCADE', ondelete='SET NULL'),
                                 nullable=True, index=True)

    @classmethod
    def bulk_insert(cls, rows, **common_values):
        return bulk_insert_into(cls, rows, **common_values)


class DefaultItemTag(DeclarativeBase):
    """
    Default tag for an item.

    For example, an user might trade with item 555 with all his toons.
    - When he assigned a tag "Ship Production" he could have statistics for all items (e.g., sum of expenses)
      for that tag.

    Another example is a corporation which lives in a wormhole (WH).
    - Tags are "PI", "sleeper sites", and "ladar sites".
    - The sum is important so that income can be divided equally amongst all WH inhabitants.
    - The tag belongs to a corporation, because all members want to see the statistics.
    Add the tag "inventory" and "running costs" to the mix and you see where this tool gets very handy.
    """
    __tablename__ = 'item_tag_defaults'
    __table_args__ = (
        UniqueConstraint('corporationID', 'tagname'),
        UniqueConstraint('user', 'tagname'),
    )

    id                  = Column(Integer, autoincrement=True, primary_key=True)
    # scope
    user_id             = Column('user', Integer,
                                 ForeignKey('users.user', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)
    corporation_id      = Column('corporationID', BigInteger,
                                 ForeignKey('corporations.corporationID', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)
    accountKey          = Column(Enum(*ACCOUNT_KEYS), default=ACCOUNT_KEYS[0], nullable=False)

    typeID              = Column(BigInteger, nullable=False, index=True)
    tagname             = Column(Unicode(128), nullable=False)


class WalletTag(DeclarativeBase):
    """
    Represents an tag of a wallet entry.

    Meant to overwrite default tags as defined by 'DefaultItemTag'.
    """
    __tablename__ = 'wallet_tag'
    __table_args__ = (
        UniqueConstraint('corporationID', 'tagname'),
        UniqueConstraint('user', 'tagname'),
    )

    tag                 = Column(Integer, autoincrement=True, primary_key=True)
    # scope
    user_id             = Column('user', Integer,
                                 ForeignKey('users.user', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)
    corporation_id      = Column('corporationID', BigInteger,
                                 ForeignKey('corporations.corporationID', onupdate='CASCADE', ondelete='CASCADE'),
                                 nullable=True, index=True)

    tagname             = Column(Unicode(128), nullable=False)

    # backrefs
    wallet_journal_entries  = relationship("WalletJournalEntry", backref="tag")
    wallet_transactions     = relationship("WalletTransaction", backref="tag")


def bulk_insert_into(cls, rows, **common_values):
    """
    Meant for bulk.inserting into tables from EVE API calls.

    rows is expected to have a list of defined columns as list row._cols.
    __conversions__ converts the names to /table/ names - not member variable names!
    """
    new_entries = []
    for row in rows:
        vals = common_values.copy()
        for colname in row._cols:
            colvalue = getattr(row, colname)
            colvalue = colvalue if colvalue != '' else None
            if colname in cls.__conversions__:
                converter = cls.__conversions__[colname]
                if len(converter) >= 2:
                    vals[converter[0]] = converter[1](colvalue)
                else:
                    vals[converter[0]] = colvalue
            elif hasattr(cls, colname):
                vals[colname] = colvalue
            else:
                logging.debug("Column %s is not part of model %r.", colname, cls)
        new_entries.append(vals)

    inserter = cls.__table__.insert().prefix_with("OR IGNORE")
    return inserter.execute(new_entries)


def test_create_tables():
    """Creates the tables in a SQLite3 database for testing purposes."""
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///test.db', echo=True)
    DeclarativeBase.metadata.create_all(engine)
