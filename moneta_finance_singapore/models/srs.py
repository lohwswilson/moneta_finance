# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaSRSTracker(models.Model):
    _name = 'moneta.srs.tracker'
    _description = 'Singapore Supplementary Retirement Scheme (SRS) Tax Relief & Withdrawal Tracker'
    _order = 'tax_year desc, id desc'

    name = fields.Char(string='SRS Tax Year Plan', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    tax_year = fields.Integer(string='Tax Assessment Year', default=lambda self: fields.Date.today().year, required=True)
    residency_status = fields.Selection([
        ('citizen_pr', 'Singapore Citizen / Permanent Resident (PR)'),
        ('foreigner', 'Foreigner / Expatriate'),
    ], string='Residency Status', default='citizen_pr', required=True)

    annual_cap = fields.Monetary(string='Annual SRS Contribution Cap', compute='_compute_srs_metrics', store=True)
    total_contributed = fields.Monetary(string='YTD SRS Contributions', compute='_compute_srs_contributions', store=True)
    remaining_allowance = fields.Monetary(string='Remaining Tax Relief Allowance', compute='_compute_srs_metrics', store=True)
    
    # IRAS Marginal Tax Rate for Tax Relief Valuation
    marginal_tax_rate = fields.Selection([
        ('0.0', '0.0% (Chargeable Income <= $20,000)'),
        ('2.0', '2.0% ($20,001 - $30,000)'),
        ('3.5', '3.5% ($30,001 - $40,000)'),
        ('7.0', '7.0% ($40,001 - $80,000)'),
        ('11.5', '11.5% ($80,001 - $120,000)'),
        ('15.0', '15.0% ($120,001 - $160,000)'),
        ('18.0', '18.0% ($160,001 - $200,000)'),
        ('19.0', '19.0% ($200,001 - $240,000)'),
        ('19.5', '19.5% ($240,001 - $280,000)'),
        ('20.0', '20.0% ($280,001 - $320,000)'),
        ('22.0', '22.0% ($320,001 - $500,000)'),
        ('23.0', '23.0% ($500,001 - $1,000,000)'),
        ('24.0', '24.0% (> $1,000,000)'),
    ], string='IRAS Marginal Tax Bracket', default='15.0', required=True)

    estimated_tax_savings = fields.Monetary(string='Estimated Income Tax Saved ($)', compute='_compute_srs_metrics', store=True)

    # 10-Year Penalty-Free Withdrawal Engine
    srs_account_id = fields.Many2one('moneta.account', string='Linked SRS Account', domain="[('account_type', '=', 'srs')]")
    srs_current_balance = fields.Monetary(related='srs_account_id.current_balance', string='SRS Current Balance', readonly=True)
    
    statutory_retirement_age = fields.Integer(string='Statutory Retirement Age (at first contribution)', default=63)
    annual_withdrawal_target = fields.Monetary(string='Planned Annual Withdrawal (10-Yr Spread)', compute='_compute_withdrawal_plan', store=True)
    annual_taxable_portion = fields.Monetary(string='50% Taxable Withdrawal / Year', compute='_compute_withdrawal_plan', store=True)
    is_tax_free_strategy = fields.Boolean(string='100% Tax-Free Strategy (<= $20k taxable/yr)', compute='_compute_withdrawal_plan', store=True)

    notes = fields.Text(string='SRS Tax Optimization Notes')

    @api.depends('tax_year', 'residency_status')
    def _compute_name(self):
        for rec in self:
            status_lbl = 'Citizen/PR' if rec.residency_status == 'citizen_pr' else 'Foreigner'
            rec.name = f"SRS Tax Relief {rec.tax_year} ({status_lbl})"

    @api.depends('residency_status', 'total_contributed', 'marginal_tax_rate')
    def _compute_srs_metrics(self):
        for rec in self:
            # Singapore SRS contribution limits: $15,300 for Citizen/PR, $35,700 for Foreigner
            cap = 15300.0 if rec.residency_status == 'citizen_pr' else 35700.0
            rec.annual_cap = cap
            contributed = rec.total_contributed or 0.0
            rec.remaining_allowance = max(cap - contributed, 0.0)

            rate = float(rec.marginal_tax_rate or 0.0) / 100.0
            rec.estimated_tax_savings = round(contributed * rate, 2)

    @api.depends('tax_year', 'user_id')
    def _compute_srs_contributions(self):
        for rec in self:
            srs_accounts = self.env['moneta.account'].search([
                ('user_id', '=', rec.user_id.id),
                ('account_type', '=', 'srs'),
            ])
            if not srs_accounts:
                rec.total_contributed = 0.0
                continue

            start_d = date(rec.tax_year, 1, 1)
            end_d = date(rec.tax_year, 12, 31)

            txs = self.env['moneta.transaction'].search([
                ('account_id', 'in', srs_accounts.ids),
                ('transaction_date', '>=', start_d),
                ('transaction_date', '<=', end_d),
                ('amount', '>', 0),
                ('state', '!=', 'void'),
            ])
            rec.total_contributed = sum(txs.mapped('amount'))

    @api.depends('srs_account_id', 'srs_current_balance')
    def _compute_withdrawal_plan(self):
        for rec in self:
            bal = rec.srs_current_balance or 0.0
            # 10-year spread
            yearly = round(bal / 10.0, 2)
            rec.annual_withdrawal_target = yearly
            # Singapore rule: 50% of withdrawal is taxable
            taxable = round(yearly * 0.50, 2)
            rec.annual_taxable_portion = taxable
            # First $20,000 of personal income is 0% tax in Singapore
            rec.is_tax_free_strategy = bool(taxable <= 20000.0)
