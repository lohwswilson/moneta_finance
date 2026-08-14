# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaProperty(models.Model):
    _name = 'moneta.property'
    _description = 'Moneta Real Estate, Property & Tangible Asset'
    _order = 'name asc'

    name = fields.Char(string='Property / Asset Name', required=True, placeholder='e.g. 123 Main St (Primary Residence)')
    property_type = fields.Selection([
        ('primary_residence', 'Primary Residence'),
        ('rental_property', 'Rental Property'),
        ('commercial', 'Commercial Real Estate'),
        ('land', 'Vacant Land / Plot'),
        ('vehicle', 'Vehicle / Automobile'),
        ('collectibles', 'Valuables & Collectibles'),
        ('other', 'Other Tangible Asset'),
    ], string='Asset Type', default='primary_residence', required=True)

    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    # Purchase & Market Valuation
    purchase_date = fields.Date(string='Purchase Date')
    purchase_price = fields.Monetary(string='Purchase Price', default=0.0)
    current_market_value = fields.Monetary(string='Estimated Market Value', required=True, default=500000.0)

    # Mortgage & Debt Linkage
    mortgage_account_id = fields.Many2one(
        'moneta.account', string='Linked Mortgage / Loan',
        domain="[('account_type', 'in', ('mortgage', 'loan', 'loc'))]",
    )
    mortgage_balance = fields.Monetary(string='Mortgage Debt Outstanding', compute='_compute_equity', store=True)
    equity_value = fields.Monetary(string='Net Home Equity ($)', compute='_compute_equity', store=True)
    loan_to_value_ratio = fields.Float(string='Loan-to-Value (LTV %)', compute='_compute_equity', store=True, digits=(5, 1))

    # Monthly Cash Flow & Expenses
    monthly_rental_income = fields.Monetary(string='Monthly Rental Income', default=0.0)
    monthly_property_tax = fields.Monetary(string='Monthly Property Tax', default=0.0)
    monthly_insurance = fields.Monetary(string='Monthly Insurance', default=0.0)
    monthly_hoa_maintenance = fields.Monetary(string='Monthly HOA / Maintenance', default=0.0)
    net_monthly_cashflow = fields.Monetary(string='Net Monthly Cash Flow', compute='_compute_cashflow', store=True)

    notes = fields.Text(string='Property Details & Records')

    @api.depends('current_market_value', 'mortgage_account_id', 'mortgage_account_id.current_balance')
    def _compute_equity(self):
        for prop in self:
            val = float(prop.current_market_value or 0.0)
            debt = 0.0
            if prop.mortgage_account_id:
                debt = abs(float(prop.mortgage_account_id.current_balance or 0.0))
            prop.mortgage_balance = round(debt, 4)
            prop.equity_value = round(max(val - debt, 0.0), 4)
            if val > 0:
                prop.loan_to_value_ratio = round((debt / val) * 100.0, 1)
            else:
                prop.loan_to_value_ratio = 0.0

    @api.depends('monthly_rental_income', 'monthly_property_tax', 'monthly_insurance', 'monthly_hoa_maintenance')
    def _compute_cashflow(self):
        for prop in self:
            inc = float(prop.monthly_rental_income or 0.0)
            tax = float(prop.monthly_property_tax or 0.0)
            ins = float(prop.monthly_insurance or 0.0)
            hoa = float(prop.monthly_hoa_maintenance or 0.0)
            prop.net_monthly_cashflow = round(inc - (tax + ins + hoa), 4)
