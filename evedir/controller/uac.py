#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from anzu.validators import error_handler, validate
from anzu.web import location, RequestHandler, redirect_path, asynchronous
from anzu import validators
from anzu.auth import GoogleMixin
from sqlalchemy import and_

from evedir.controller.bases import BaseHandler
from evedir.model import User, Keypair, Toon, Corporation

import eveapi


redirect_path('^/$', '/login')
@location('/login')
class LoginHandler(BaseHandler):
    def get(self, was_login_attempted=False):
        user = self.get_current_user()
        # redirect those who want to log in twice ;-)
        if user:
            self.redirect(self.get_argument('forward_url', '/dashboard'))
            return
        # cookie with nonexistant user
        elif self.get_secure_cookie("user"):
            logging.debug("Field 'user' in secure cookie has been found but does not match any user in our database. ID=%d",
                          self.get_secure_cookie("user"))
            self.clear_cookie("user")

        _ = self.locale.translate
        msg = None
        # optional error handling
        self.set_status(403)
        if was_login_attempted:
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif self.has_validation_errors:
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg=_("Please log in.")
            self.set_status(200)

        self.render("login.html", message=msg, forward_url=self.get_argument('next', None))

    @error_handler(get)
    @validate(validators={'email': validators.Email(not_empty=True, min=7, max=64),
                          'password': validators.UnicodeString(not_empty=True, min=6, max=32, strip=False)})
    def post(self):
        user = self.db.query(User).filter(and_(User.email_address == self.value_for('email'), User.enabled == True)).first()

        if user and user.validate_password(self.value_for('password')):
            self.set_secure_cookie("user", str(user.id))
            self.redirect(self.get_argument('forward_url', '/dashboard'))
        else:
            self.get(was_login_attempted=True)


@location('/login/by_google')
class GoogleAuthHandler(BaseHandler, GoogleMixin):
    @asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user):
        _ = self.locale.translate
        if not user:
            self.set_status(403)
            msg=_("Google auth failed.")
            self.render("login.html", message=msg, forward_url=self.get_argument('next', None))
            return

        logging.debug("Google authentication came back with %r", user)
        user = self.db.query(User).filter(and_(User.email_address == user['email'], User.enabled == True)).first()
        if user:
            self.set_secure_cookie("user", str(user.id))
            self.redirect(self.get_argument('forward_url', '/dashboard'))
        else:
            self.set_status(403)
            msg=_("Sorry, we couldn't find you in our database.")
            self.render("login.html", message=msg, forward_url=self.get_argument('next', None))


@location('/logout')
class LogoutHandler(RequestHandler):
    def get(self):
        if self.get_secure_cookie("user"):
            self.clear_cookie("user")
        self.redirect(self.get_login_url())


@location('/register')
class RegistrationHandler(BaseHandler):
    def get(self, errors=[]):
        self.render("registration.html", errors=errors)

    register_fields = {
        'email': validators.Email(not_empty=True, min=7, max=64),
        'password': validators.UnicodeString(not_empty=True, min=6, max=32, strip=False),
        'keyID': validators.Int(not_emptry=True, min=1),
        'vCode': validators.UnicodeString(not_empty=True, min=56, max=128, strip=True),
    }

    @error_handler(get)
    @validate(validators=register_fields)
    def post(self):
        _ = self.locale.translate
        errors = []
        # is the email address already in use?
        user = self.db.query(User).filter(User.email_address == self.value_for('email')).first()
        if user:
            logging.debug('Email address "%s" is already known and registration aborted.', user.email_address)
            self.set_status(409)
            errors.append(_("Sorry, but the email address is already registered with us. Did you forget your password?"))

        # Does the API key work at all?
        logging.debug('About to fetch data from the EVE API servers.')
        auth = self.get_eveapi_for(keyID=self.value_for('keyID'), vCode=self.value_for('vCode'))
        try:
            keyinfo = auth.account.APIKeyInfo()
            characters = keyinfo.key.characters
        except eveapi.Error, e:
            self.set_status(400)
            self.request.validation_errors = {
                'keyID': _("check this"),
                'vCode': _("check that"),
            }
            errors.append(_('Having been presented your API keys, the EVE Online server said: "%s"') % e)
            return self.get(errors=errors)
        logging.debug('%d characters are associated with keyID %d.', len(characters), self.value_for('keyID'))
        toon_ids = [int(character.characterID) for character in characters]

        # Create the new user.
        if not errors:
            # corporations, if missing
            corps = {}
            for character in characters:
                corps[character.corporationID] = character.corporationName
            for corporationID in corps:
                c = self.db.query(Corporation).filter(Corporation.corporationID == corporationID).first()
                if not c: # corporation is unknown
                    logging.debug('Corporation "%s" (%d) is new to us. Adding.', corps[corporationID], corporationID)
                    self.db.add(Corporation(corporationID = corporationID, name=corps[corporationID]))
            self.db.commit()

            # account
            user = User(
                name=self.value_for('email'),
                email_address=self.value_for('email'),
                timezone='Europe/Berlin',
                password=self.value_for('password')
            )
            self.db.add(user)
            # keypair
            keypair = Keypair(
                holder=user,
                keyID=self.value_for('keyID'),
                vCode=self.value_for('vCode'),
                accessMask=long(keyinfo.key.accessMask),
                type=keyinfo.key.type,
                corporationID=keyinfo.key.characters[0].corporationID if keyinfo.key.type == 'Corporation' else None,
                characterID=keyinfo.key.characters[0].characterID if keyinfo.key.type == 'Corporation' else None,
            )
            self.db.add(keypair)
            # characters
            if keypair.type != 'Corporation':
                for character in characters:
                    c = self.db.query(Toon).filter(Toon.characterID == character.characterID).first()
                    if not c:
                        logging.debug('About to add toon "%s" (%d) to account of "%s".', character.characterName, character.characterID, user.email_address)
                        self.db.add(Toon(
                            characterID=character.characterID,
                            name=character.characterName,
                            corporation_id=character.corporationID,
                            holder=user
                        ))
            logging.debug('About to commit data for new account belonging to "%s".', user.email_address)
            self.db.commit()
            logging.info('The account has been created! Redirecting user "%s".', user.email_address)
            self.redirect('/login')
        else:
            self.get(errors=errors)
