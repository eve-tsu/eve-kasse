#!/usr/bin/env python
# -*- coding: utf-8 -*-

from anzu.web import RequestHandler
from sqlalchemy import and_

from evedir.model import User

__all__ = [
    'DatabaseMixin', 'BaseHandler', 'EveApiAccessorMixin',
]

class DatabaseMixin(object):
    """
    Enables RequestHandlers to use the database safely.
    """

    @property
    def db(self):
        if not hasattr(self, '_db'):
            self._db = self.application._db()
        return self._db


class EveApiAccessorMixin(object):

    def get_eveapi_for(self, keyID, vCode):
        api = self.application.eveapi
        return api.auth(keyID=keyID, vCode=vCode)


class BaseHandler(RequestHandler, DatabaseMixin, EveApiAccessorMixin):

    def get_current_user(self):
        user = getattr(self, '_user', None)
        if user:
            return user
        user_id = self.get_secure_cookie("user")
        if user_id:
            self._user = self.db.query(User).filter(and_(User.id == int(user_id), User.enabled == True)).first()
            return self._user
        return None

# Example decorator:
#def has_permission(permission):
#    def entangle(method):
#        @functools.wraps(method)
#        def wrapper(self, *args, **kwargs):
#            current_user = self.current_user
#            if not (current_user and current_user.permission and getattr(current_user.permission, permission, False)):
#                logging.warn('User "%s" does not have permission "%s"', current_user.email_address, permission)
#                raise HTTPError(403) # forbidden
#            return method(self, *args, **kwargs)
#        return wrapper
#    return entangle
