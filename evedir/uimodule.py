#!/usr/bin/env python
# -*- coding: utf-8 -*-

from anzu.web import UIModule

__all__ = [
    'QuickstartMisc',
]

# Instances of UIModule go here!

class QuickstartMisc(UIModule):
    """
    Example collector of miscellaneous functions.
    """

    def render(self):
        return ''

    def javascript_files(self):
        return [
            "javascript/prototype.js",
            "javascript/scriptaculous.js",
            "javascript/effects.js",
            "javascript/thirdparty/cookie.js",
            "javascript/evedir.js",
        ]

    def css_files(self):
        return [
#            "css/default.css",
        ]
