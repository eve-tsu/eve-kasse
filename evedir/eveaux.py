import logging

from evedir.model import ACCOUNT_KEYS, WalletJournalEntry, WalletTransaction

def sync_wallet(keypair, eveapi_ctx):
    api = eveapi_ctx.auth(keyID=keypair.keyID, vCode=keypair.vCode)
    is_corpkey = keypair.type == 'Corporation'

    if not (keypair.grants_access_to('WalletJournal') and keypair.grants_access_to('WalletTransactions')):
        logging.debug('Keypair %r does not grant access to wallet. Skipping.', keypair)
        return

    # determine char/corp/wallet combinations
    combinations = []
    if is_corpkey:
        for accountKey in ACCOUNT_KEYS:
            combinations.append({'characterID': keypair.characterID, 'accountKey': accountKey})
    else:
        # fetch the associated toons
        keyinfo = api.account.APIKeyInfo()
        for character in keyinfo.key.characters:
            combinations.append({'characterID': int(character.characterID), 'accountKey': ACCOUNT_KEYS[0]})

    # do the magic
    for params in combinations:
        params['rowCount'] = 2560

        # journal
        response = api.corp.WalletJournal(**params) if is_corpkey else api.char.WalletJournal(**params)
        rows = response.entries if hasattr(response, 'entries') else response.transactions
        logging.debug('Got %d wallet journal entries for keypair %d, account %s.',
                      len(rows), keypair.keyID, params['accountKey'])
        if len(rows) > 0:
            WalletJournalEntry.bulk_insert(
                rows,
                accountKey = params['accountKey'],
                corporationID = keypair.corporationID if is_corpkey else None,
                character = params['characterID'] if not is_corpkey else None
            )

        # transactions
        response = api.corp.WalletTransactions(**params) if is_corpkey else api.char.WalletTransactions(**params)
        rows = response.entries if hasattr(response, 'entries') else response.transactions
        logging.debug('Got %d wallet transactions for keypair %d, account %s.',
                      len(rows), keypair.keyID, params['accountKey'])
        if len(rows) > 0:
            WalletTransaction.bulk_insert(
                rows,
                accountKey = params['accountKey'],
                corporationID = keypair.corporationID if is_corpkey else None,
                character = params['characterID'] if not is_corpkey else None
            )
