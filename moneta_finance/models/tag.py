# -*- coding: utf-8 -*-
from odoo import models, fields

class MonetaTag(models.Model):
    _name = 'moneta.tag'
    _description = 'Moneta Transaction Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index', default=0)
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )
