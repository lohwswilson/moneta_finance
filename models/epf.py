# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaEpfAccount(models.Model):
    _name = 'moneta.epf.account'
    _description = 'Malaysia EPF / KWSP 3-Account Retirement Hub'
    _order = 'name asc'

    name = fields.Char(string='Member Name / Description', required=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    epf_member_number = fields.Char(string='KWSP / EPF Member #')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.MYR', raise_if_not_found=False) or self.env.company.currency_id, required=True)

    scheme_type = fields.Selection([
        ('conventional', 'Simpanan Konvensional'),
        ('shariah', 'Simpanan Shariah'),
    ], string='EPF Scheme Type', default='conventional', required=True)

    # Post-May 2024 3-Account Structure
    account_1_persaraan = fields.Monetary(
        string='Akaun Persaraan (Akaun 1 - 75%)',
        help='Retirement account locked until age 55 for long-term retirement security.',
        default=0.0,
    )
    account_2_sejahtera = fields.Monetary(
        string='Akaun Sejahtera (Akaun 2 - 15%)',
        help='Flexible account for housing purchase/loan repayment, education, medical, and age 50 withdrawal.',
        default=0.0,
    )
    account_3_fleksibel = fields.Monetary(
        string='Akaun Fleksibel (Akaun 3 - 10%)',
        help='Emergency liquid savings account accessible anytime for cash withdrawals.',
        default=0.0,
    )

    total_epf_balance = fields.Monetary(
        string='Total KWSP / EPF Balance',
        compute='_compute_epf_totals',
        store=True,
    )

    # Contribution & Dividend Rates
    monthly_employee_rate = fields.Float(string='Employee Contribution Rate (%)', default=11.0, digits=(4, 1))
    monthly_employer_rate = fields.Float(string='Employer Contribution Rate (%)', default=12.0, digits=(4, 1))
    projected_dividend_rate = fields.Float(string='Projected Dividend Rate (%)', default=5.50, digits=(4, 2))
    projected_annual_dividend = fields.Monetary(string='Projected Annual Dividend', compute='_compute_epf_totals', store=True)

    # i-Saraan / Voluntary Self-Contribution (up to RM100,000 / year)
    i_saraan_voluntary_ytd = fields.Monetary(string='i-Saraan / Self-Contribution YTD', default=0.0)
    i_saraan_matching_incentive = fields.Monetary(
        string='Govt 15% Matching Incentive (Max RM500)',
        compute='_compute_isaraan_incentive',
        store=True,
    )

    transaction_ids = fields.One2many('moneta.epf.transaction', 'epf_account_id', string='Contribution & Withdrawal Ledger')
    notes = fields.Text(string='Notes / Nomination Details')

    @api.depends('account_1_persaraan', 'account_2_sejahtera', 'account_3_fleksibel', 'projected_dividend_rate')
    def _compute_epf_totals(self):
        for rec in self:
            a1 = float(rec.account_1_persaraan or 0.0)
            a2 = float(rec.account_2_sejahtera or 0.0)
            a3 = float(rec.account_3_fleksibel or 0.0)
            total = a1 + a2 + a3
            rec.total_epf_balance = round(total, 2)
            rec.projected_annual_dividend = round(total * (float(rec.projected_dividend_rate or 5.5) / 100.0), 2)

    @api.depends('i_saraan_voluntary_ytd')
    def _compute_isaraan_incentive(self):
        for rec in self:
            contrib = float(rec.i_saraan_voluntary_ytd or 0.0)
            # 15% matching incentive capped at RM500 per calendar year
            matching = min(contrib * 0.15, 500.0)
            rec.i_saraan_matching_incentive = round(matching, 2)


class MonetaEpfTransaction(models.Model):
    _name = 'moneta.epf.transaction'
    _description = 'EPF / KWSP Contribution & Withdrawal Record'
    _order = 'transaction_date desc, id desc'

    epf_account_id = fields.Many2one('moneta.epf.account', string='EPF Account', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='epf_account_id.currency_id')
    transaction_date = fields.Date(string='Transaction Date', default=fields.Date.context_today, required=True)

    transaction_type = fields.Selection([
        ('monthly_salary_contribution', 'Monthly Salary Contribution (75/15/10 Split)'),
        ('i_saraan_voluntary', 'i-Saraan / Self-Contribution'),
        ('annual_dividend', 'Annual Dividend Credited'),
        ('withdrawal_housing', 'Akaun Sejahtera: Housing Purchase / Loan Repayment'),
        ('withdrawal_education', 'Akaun Sejahtera: Education Withdrawal'),
        ('withdrawal_medical', 'Akaun Sejahtera: Medical Treatment'),
        ('withdrawal_fleksibel', 'Akaun Fleksibel: Anytime Cash Withdrawal'),
        ('transfer_account', 'Inter-Account Transfer (e.g. Sejahtera to Fleksibel)'),
    ], string='Transaction Type', default='monthly_salary_contribution', required=True)

    amount_total = fields.Monetary(string='Total Amount', required=True, default=0.0)
    amount_account_1 = fields.Monetary(string='Akaun Persaraan (75%)', compute='_compute_split_amounts', store=True, readonly=False)
    amount_account_2 = fields.Monetary(string='Akaun Sejahtera (15%)', compute='_compute_split_amounts', store=True, readonly=False)
    amount_account_3 = fields.Monetary(string='Akaun Fleksibel (10%)', compute='_compute_split_amounts', store=True, readonly=False)

    notes = fields.Char(string='Reference / Notes')

    @api.depends('amount_total', 'transaction_type')
    def _compute_split_amounts(self):
        for rec in self:
            tot = float(rec.amount_total or 0.0)
            if rec.transaction_type in ('monthly_salary_contribution', 'i_saraan_voluntary', 'annual_dividend'):
                rec.amount_account_1 = round(tot * 0.75, 2)
                rec.amount_account_2 = round(tot * 0.15, 2)
                rec.amount_account_3 = round(tot * 0.10, 2)
            elif rec.transaction_type in ('withdrawal_housing', 'withdrawal_education', 'withdrawal_medical'):
                rec.amount_account_1 = 0.0
                rec.amount_account_2 = -abs(tot)
                rec.amount_account_3 = 0.0
            elif rec.transaction_type == 'withdrawal_fleksibel':
                rec.amount_account_1 = 0.0
                rec.amount_account_2 = 0.0
                rec.amount_account_3 = -abs(tot)
