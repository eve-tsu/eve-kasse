#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from anzu.validators import error_handler, validate
from anzu.web import location, RequestHandler, redirect_path, asynchronous
from anzu import validators
from anzu.auth import GoogleMixin
from sqlalchemy import and_

from evedir.controller.bases import BaseHandler
from evedir.model import User


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
