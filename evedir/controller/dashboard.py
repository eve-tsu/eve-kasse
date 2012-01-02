# -*- coding: utf-8 -*-

import logging
from anzu.web import location, authenticated, path

from evedir.controller.bases import BaseHandler
from uac import RegistrationHandler

@location('/dashboard')
class DashboardHandler(BaseHandler):

    @authenticated
    def get(self):
        user = self.get_current_user()
        self.render("dashboard.html", toons=user.toons)


@location('/keypairs')
class KeypairHandler(BaseHandler):

    @authenticated
    def get(self):
        self.render("keypairs.html")

    new_keys_fields = {
        'keyID': RegistrationHandler.register_fields['keyID'],
        'vCode': RegistrationHandler.register_fields['vCode'],
    }

#    @authenticated
#    @error_handler(get)
#    @validate(validators=new_keys_fields)
#    def post(self):
#        _ = self.locale.translate
#        errors = []

from anzu.validators import error_handler, validate
from anzu import validators
from anzu.web import HTTPError
from sqlalchemy import and_, func, exceptions as sql_exc

from evedir.model import WalletJournalEntry, WalletTransaction, DefaultItemTag, WalletTag, ACCOUNT_KEYS

@location('/tagging')
class TaggingLanding(BaseHandler):

    @authenticated
    def get(self):
        # get statistics
        self.render("wallet_tags/main.html")


@path('/tagging/(corp)/(\d+)/(100[0-6])/add_default')
@path('/tagging/(user)/(\d+)/(1000)/add_default')
class AddTagsHelper(BaseHandler):

    @authenticated
    def get(self, corc, corc_id, accountKey):
        if not accountKey in ACCOUNT_KEYS:
            raise HTTPError(409)

        # get one random item w/o default tag
        untagged = self.db.query(WalletTransaction.typeID, WalletTransaction.typeName) \
                    .filter(and_(WalletTransaction.tag_id == None, WalletTransaction.accountKey == accountKey))

        # get tags and their occurence
        tags = {}
        if untagged:
            is_wallettag_owner = WalletTag.corporation_id == corc_id if corc == 'corp' else WalletTag.user_id == corc_id
            is_default_tag_owner = DefaultItemTag.corporation_id == corc_id if corc == 'corp' else DefaultItemTag.user_id == corc_id

            # all wallet tags, but w/o counting their occurence
            all_tags = self.db.query(WalletTag.tagname).filter(is_wallettag_owner)
            logging.debug("Total tags: %d", all_tags.count())
            for tag in all_tags:
                tags[tag[0]] = {'num': 0, 'other': True}

            # default tags
            def_tags = self.db.query(DefaultItemTag.tagname).filter(
                and_(is_default_tag_owner, DefaultItemTag.accountKey == str(accountKey))
            )
            logging.debug("Total default tags: %d", def_tags.count())
            for tag in def_tags:
                tags[tag[0]] = {'num': 0, 'other': False}

            # wallet tags, current account
            sum_tags = 0
            sum_count = 0
            current_tags = self.db.query(WalletTag.tagname, func.count(WalletTransaction.transactionID)) \
                .outerjoin(WalletTransaction) \
                .filter(and_(is_wallettag_owner, WalletTransaction.accountKey == str(accountKey))) \
                .group_by(WalletTag.tagname)
            logging.debug("Total used tags: %d", current_tags.count())
            for tag, count in current_tags:
                tags[tag] = {'num': count, 'other': False}
                sum_tags += 1
                sum_count += count
            tag_average = sum_count / sum_tags if sum_tags > 0 else 1
        else:
            tags = {}
            tag_average = 1

        self.render("wallet_tags/add_default.html",
                    untagged=untagged.first(), tags=tags, tag_average=tag_average,
                    basesize = 140)

    default_item_tag_fields = {
        'typeID': validators.Int(not_emptry=True, min=1),
        'tagname': validators.UnicodeString(not_empty=True, min=3, max=128, strip=True),
    }

    @error_handler(get)
    @validate(validators=default_item_tag_fields)
    @authenticated
    def post(self, corc, corc_id, accountKey):
        if not accountKey in ACCOUNT_KEYS:
            raise HTTPError(409)

        is_wallettag_owner = WalletTag.corporation_id == corc_id if corc == 'corp' else WalletTag.user_id == corc_id
        is_default_tag_owner = DefaultItemTag.corporation_id == corc_id if corc == 'corp' else DefaultItemTag.user_id == corc_id

        # store
        deftag = DefaultItemTag(
            user_id = corc_id if corc == 'user' else None,
            corporation_id = corc_id if corc == 'corp' else None,
            typeID = self.value_for('typeID'),
            tagname = self.value_for('tagname'),
        )
        self.db.merge(deftag) # duplicate? ignore
        try:
            self.db.commit()
        except sql_exc.IntegrityError:
            self.db.rollback()

        tag = WalletTag(
            user_id = corc_id if corc == 'user' else None,
            corporation_id = corc_id if corc == 'corp' else None,
            tagname = self.value_for('tagname'),
        )
        self.db.merge(tag)
        try:
            self.db.commit() # duplicate? ignore
        except sql_exc.IntegrityError:
            self.db.rollback()

        # apply
        tag = self.db.query(WalletTag).filter(
            and_(WalletTag.corporation_id == corc_id if corc == 'corp' else WalletTag.user_id == corc_id,
                 WalletTag.tagname == self.value_for('tagname'),
                 )
        ).first()
        if tag:
            self.db.query(WalletTransaction).filter(
                and_(
                    WalletTransaction.corporation_id == corc_id if corc == 'corp' else WalletTransaction.user_id == corc_id,
                    WalletTransaction.typeID == deftag.typeID,
                    WalletTransaction.tag_id == None
                )
            ).update({WalletTransaction.tag_id: tag.tag})
            self.db.commit()
        else:
            self.set_status(410)
            logging.warning('An expected tag has gone away.')

        # display get
        self.get(corc, corc_id, accountKey)


@location('/reports')
class ReportsHandler(BaseHandler):

    @authenticated
    def get(self):
        self.redirect('/report/corp/1231001270/1006')


@path('/report/(corp)/(\d+)/(100[0-6])')
@path('/report/(char)/(\d+)/(1000)')
class ReportGenerator(BaseHandler):

    @authenticated
    def get(self, corc, corc_id, accountKey):
        aio = {}
        # --- Wallet Transactions
        is_owner = WalletTransaction.corporation_id == corc_id if corc == 'corp' else WalletTransaction.character_id == corc_id

        # sell
        ts = self.db.query(WalletTag.tagname, func.sum(WalletTransaction.quantity * WalletTransaction.price)) \
            .join(WalletTransaction) \
            .filter(and_(is_owner, WalletTransaction.transactionType == 'sell', WalletTransaction.accountKey == accountKey)) \
            .group_by(WalletTag.tagname)
        for tagname, sum in ts:
            aio[tagname] = {'sell': sum, 'buy': 0}

        # buy
        tb = self.db.query(WalletTag.tagname, func.sum(WalletTransaction.quantity * WalletTransaction.price)) \
            .join(WalletTransaction) \
            .filter(and_(is_owner, WalletTransaction.transactionType == 'buy', WalletTransaction.accountKey == accountKey)) \
            .group_by(WalletTag.tagname)
        for tagname, sum in tb:
            if tagname in aio:
                aio[tagname]['buy'] = sum
            else:
                aio[tagname] = {'sell': 0, 'buy': sum}

        # --- Journal Entries
        is_owner = WalletJournalEntry.corporation_id == corc_id if corc == 'corp' else WalletJournalEntry.character_id == corc_id

        # 10 --> deposits
        jd = self.db.query(WalletJournalEntry.ownerName1, func.sum(WalletJournalEntry.amount)) \
            .filter(and_(is_owner, WalletJournalEntry.refTypeID == 10, WalletJournalEntry.accountKey == accountKey)) \
            .group_by(WalletJournalEntry.ownerName1)
        deposits_payouts = [(name, amount) for name, amount in jd]

        # 37 --> payouts
        jd = self.db.query(WalletJournalEntry.ownerName2, func.sum(WalletJournalEntry.amount)) \
            .filter(and_(is_owner, WalletJournalEntry.refTypeID == 37, WalletJournalEntry.accountKey == accountKey)) \
            .group_by(WalletJournalEntry.ownerName2)
        deposits_payouts += [(name, amount) for name, amount in jd]

        # --- Journal Entries - Details
        # 10 --> deposits
        jd = self.db.query(WalletJournalEntry.ownerName1, WalletJournalEntry.amount, WalletJournalEntry.reason, WalletJournalEntry.ownerName2) \
            .filter(and_(is_owner, WalletJournalEntry.refTypeID == 10, WalletJournalEntry.accountKey == accountKey))
        deposits_payouts_details = [(name, amount, reason, other) for name, amount, reason, other in jd]

        # 37 --> payouts
        jd = self.db.query(WalletJournalEntry.ownerName2, WalletJournalEntry.amount, WalletJournalEntry.reason, WalletJournalEntry.argName1) \
            .filter(and_(is_owner, WalletJournalEntry.refTypeID == 37, WalletJournalEntry.accountKey == accountKey))
        deposits_payouts_details += [(name, amount, reason, other) for name, amount, reason, other in jd]

        self.render('reports/sheet.html',
                    transactions_by_tag = aio,
                    deposits_payouts = deposits_payouts,
                    deposits_payouts_details = deposits_payouts_details)
