#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from time import sleep
from datetime import datetime

from sqlalchemy import exc, or_, and_
from anzu.options import options
from anzu.httpclient import HTTPError

import eveapi
from evedir.model import Keypair
from evedir.eveaux import sync_wallet

__all__ = ['wallet_synchronization']

def keypairs_with_wallet_access(db):
    """
    Gets keypairs which enable us to read wallet journal and transactions.
    """
    now = datetime.utcnow()
    key_is_working = and_(
        Keypair.valid == True,
        or_(Keypair.expires < now, Keypair.expires == None)
    )
    key_grants_wallet_access = or_(
        and_(Keypair.type == 'Corporation',
             Keypair.accessMask > max(Keypair.ACCESS['Corporation']['WalletJournal'], Keypair.ACCESS['Corporation']['WalletTransactions']),
             Keypair.accessMask.op('&')(Keypair.ACCESS['Corporation']['WalletJournal']),
             Keypair.accessMask.op('&')(Keypair.ACCESS['Corporation']['WalletTransactions'])),
        and_(Keypair.type != 'Corporation',
             Keypair.accessMask > max(Keypair.ACCESS['Character']['WalletJournal'], Keypair.ACCESS['Character']['WalletTransactions']),
             Keypair.accessMask.op('&')(Keypair.ACCESS['Character']['WalletJournal']),
             Keypair.accessMask.op('&')(Keypair.ACCESS['Character']['WalletTransactions'])),
    )
    keypairs = db.query(Keypair) \
        .filter(key_is_working) \
        .filter(key_grants_wallet_access)
    return keypairs


def wallet_synchronization(sessionmaker):
    logging.info("Wallet synchronization has been started.")
    eveapi_ctx = eveapi.EVEAPIConnection(cacheHandler=eveapi.RedisEVEAPICacheHandler())
    db = sessionmaker()
    sleep(20) # some seconds to get everything started

    while True:
        start = datetime.utcnow()
        keypairs = keypairs_with_wallet_access(db)
        logging.info('Wallet synchronization triggered.')

        for keypair in keypairs:
            try:
                logging.debug('Syncing wallets of key with keyID=%d', keypair.keyID)
                sync_wallet(keypair, eveapi_ctx)
            except HTTPError, e:
                logging.warning('HTTP Error %r', e)
            except Exception, e:
                logging.exception("Unhandled exception %s", e)
                if options.debug:
                    raise
                else:
                    # do nothing, the service must keep going on
                    pass

        seconds_passed = (datetime.utcnow() - start).seconds
        seconds_to_sleep = options.sync_wallets_every * 3600 - seconds_passed
        logging.info('Wallet synchronization run is complete. Will sleep for %d seconds.', seconds_to_sleep)
        sleep(seconds_to_sleep)
