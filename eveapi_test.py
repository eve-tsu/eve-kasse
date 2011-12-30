import eveapi

api = eveapi.EVEAPIConnection()

auth = api.auth(
    keyID = '373820',
    vCode = 'WrN9iho6Jm3FEsgMBBX12eR2jobThb4V0d0P0Wa0uVWXJEcO6jhERwNCHcxUu2TK'
)

result2 = auth.account.Characters()

# Some tracking for later examples.
rich = 0
rich_charID = 0

# Now the best way to iterate over the characters on your account and show
# the isk balance is probably this way:
for character in result2.characters:
    print character.name, character
#    wallet = auth.char.AccountBalance(characterID=character.characterID)
#    isk = wallet.accounts[0].balance
#    print character.name, "has", isk, "ISK."
#    print character
