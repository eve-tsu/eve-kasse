# -*- coding: utf-8 -*-

from os import path
from datetime import datetime
import logging

from anzu.options import options
from anzu.web import location, authenticated
from anzu.validators import error_handler, validate, InputInvalidException
from anzu import validators
from sqlalchemy import exc

from evedir.controller.bases import BaseHandler
from evedir.model import Campaign

__all__ = ['NewCampaignHandler']

@location('/campaign/new')
class NewCampaignHandler(BaseHandler):

    @authenticated
    def get(self):
        self.render("new_campaign_form.html", message=None)

    @authenticated
    @error_handler(get)
    @validate(validators={'title':              validators.UnicodeString(not_empty=True, min=6, max=64, strip=True),
                          'egress_address':     validators.Email(not_empty=False, min=7, max=64),
                          'collect_clickdata':  validators.StringBool(),
                          })
    def post(self):
        _ = self.locale.translate
        if not 'merger_file' in self.request.files:
            self.request.validation_errors['merger_file'] = _("Required file is missing.")
            self.set_status(400)
            raise InputInvalidException()

        merger_file = self.request.files['merger_file'][0]
        now = datetime.utcnow()
        output_filename = "%d-%02d-%02dT%02d-%02d-%02d_user%03d.csv" \
                          % (now.year, now.month, now.day, now.hour, now.minute, now.second, self.current_user.id)
        with open(path.join(options.file_storage, output_filename), 'w') as f:
            f.write(merger_file['body'])

        new_campaign = Campaign(
            title = self.value_for('title'),
            merger_file = output_filename,
            collect_clickdata = self.value_for('collect_clickdata') or False,
            egress_address = self.value_for('egress_address'),
            creator = self.current_user,
        )

        self.db.add(new_campaign)
        try:
            self.db.commit()
            self.redirect(self.get_argument('forward_url', '/dashboard'))
        except exc.DatabaseError, e:
            self.set_status(400)
            self.render("new_campaign_form.html",
                        message=_('Error while creating new campaign: <span class="fielderror">%s</span>') % e.orig)
