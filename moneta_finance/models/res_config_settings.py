# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Main Base Currency',
        readonly=False,
        help='Main base reporting currency for your accounts and reports.'
    )
    group_multi_currency = fields.Boolean(
        string='Multi-Currencies',
        implied_group='base.group_multi_currency',
        help='Allows multi-currency bank accounts, transfers, and foreign currency exchange rates.'
    )
