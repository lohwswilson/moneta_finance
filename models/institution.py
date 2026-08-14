# -*- coding: utf-8 -*-
from odoo import models, fields


class MonetaInstitution(models.Model):
    _name = 'moneta.institution'
    _description = 'Moneta Financial Institution'
    _order = 'name'

    name = fields.Char(string='Institution Name', required=True)
    website = fields.Char(string='Website')
    country = fields.Char(
        string='Country Code', size=2,
        help='ISO 3166-1 alpha-2 country code (e.g. SG, US, UK, MY)',
    )
    bank_profile = fields.Selection([
        ('auto', 'Universal Smart Auto-Detect'),
        ('dbs_posb', 'DBS / POSB Bank (Singapore)'),
        ('ocbc', 'OCBC Bank (Singapore)'),
        ('uob', 'UOB United Overseas Bank (Singapore)'),
        ('citi', 'Citibank (Singapore & Global)'),
        ('sc', 'Standard Chartered Bank'),
        ('hsbc', 'HSBC Bank'),
        ('wise', 'Wise (TransferWise)'),
        ('revolut', 'Revolut Multi-Currency'),
        ('chase', 'Chase Bank (US)'),
        ('bofa', 'Bank of America (US)'),
        ('amex', 'American Express (Global)'),
        ('maybank', 'Maybank / CIMB'),
        ('custom', 'Custom CSV Mapping Preset'),
    ], string='Statement CSV Profile', default='auto', required=True,
       help='Pre-configured parser profile for parsing statement exports and PayNow/GIRO narrations.')

    # Custom Column Mapping Presets (1-based column indices; 0 = auto-detect)
    csv_has_header = fields.Boolean(string='CSV Has Header Row', default=True)
    csv_date_col = fields.Integer(string='Default Date Column', default=0)
    csv_payee_col = fields.Integer(string='Default Payee Column', default=0)
    csv_amount_col = fields.Integer(string='Default Amount Column', default=0)
    csv_debit_col = fields.Integer(string='Default Debit Column', default=0)
    csv_credit_col = fields.Integer(string='Default Credit Column', default=0)
    csv_category_col = fields.Integer(string='Default Category Column', default=0)
    csv_memo_col = fields.Integer(string='Default Memo Column', default=0)

    active = fields.Boolean(default=True)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    _sql_constraints = [
        ('unique_user_name', 'unique(user_id, name)',
         'An institution with this name already exists for this user.'),
    ]
