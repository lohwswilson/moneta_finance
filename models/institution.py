# -*- coding: utf-8 -*-
from odoo import models, fields


class MonetaInstitution(models.Model):
    _name = 'moneta.institution'
    _description = 'Moneta Financial Institution'
    _order = 'name'

    # Mirrors Moneta's institutions entity (name + website + country), minus the
    # cached-logo/favicon fields, which are deferred for the MVP.
    name = fields.Char(string='Institution Name', required=True)
    website = fields.Char(string='Website')
    country = fields.Char(
        string='Country Code', size=2,
        help='ISO 3166-1 alpha-2 country code',
    )
    active = fields.Boolean(default=True)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    _sql_constraints = [
        # Faithful to Moneta's @Unique(["userId", "name"]).
        ('unique_user_name', 'unique(user_id, name)',
         'An institution with this name already exists for this user.'),
    ]