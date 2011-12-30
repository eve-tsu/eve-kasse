# -*- coding: utf-8 -*-

import logging
from anzu.web import location, authenticated

from evedir.controller.bases import BaseHandler
from evedir.model import Campaign

@location('/dashboard')
class DashboardHandler(BaseHandler):

        @authenticated
        def get(self):
            archived_campaigns = []
            campaigns = []
            for c in self.db.query(Campaign):
                if c.archived:
                    archived_campaigns.append(c)
                else:
                    campaigns.append(c)
            self.render("dashboard.html",
                        campaigns=campaigns, archived_campaigns=archived_campaigns)
