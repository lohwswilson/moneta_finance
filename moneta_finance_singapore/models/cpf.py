# -*- coding: utf-8 -*-
import json
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class MonetaAccountCPF(models.Model):
    _inherit = 'moneta.account'

    # CPF-specific interest computation and status
    is_cpf = fields.Boolean(string='Is CPF Account', compute='_compute_is_cpf', store=True)
    cpf_account_type = fields.Selection([
        ('oa', 'Ordinary Account (OA) - 2.50% p.a.'),
        ('sa', 'Special Account (SA) - 4.00% p.a.'),
        ('ma', 'MediSave Account (MA) - 4.00% p.a.'),
        ('ra', 'Retirement Account (RA) - 4.00% p.a.'),
    ], string='CPF Account Subtype', compute='_compute_is_cpf', store=True)

    @api.depends('account_type')
    def _compute_is_cpf(self):
        for acc in self:
            if acc.account_type == 'cpf_oa':
                acc.is_cpf = True
                acc.cpf_account_type = 'oa'
            elif acc.account_type == 'cpf_sa':
                acc.is_cpf = True
                acc.cpf_account_type = 'sa'
            elif acc.account_type == 'cpf_ma':
                acc.is_cpf = True
                acc.cpf_account_type = 'ma'
            elif acc.account_type == 'cpf_ra':
                acc.is_cpf = True
                acc.cpf_account_type = 'ra'
            else:
                acc.is_cpf = False
                acc.cpf_account_type = False

    @api.onchange('account_type')
    def _onchange_cpf_account_type(self):
        if self.account_type == 'cpf_oa':
            self.interest_rate = 2.50
            if not self.name or self.name == 'New Account':
                self.name = 'CPF Ordinary Account (OA)'
        elif self.account_type == 'cpf_sa':
            self.interest_rate = 4.00
            if not self.name or self.name == 'New Account':
                self.name = 'CPF Special Account (SA)'
        elif self.account_type == 'cpf_ma':
            self.interest_rate = 4.00
            if not self.name or self.name == 'New Account':
                self.name = 'CPF MediSave Account (MA)'
        elif self.account_type == 'cpf_ra':
            self.interest_rate = 4.00
            if not self.name or self.name == 'New Account':
                self.name = 'CPF Retirement Account (RA)'
        elif self.account_type == 'srs':
            if not self.name or self.name == 'New Account':
                self.name = 'Supplementary Retirement Scheme (SRS)'

    def calculate_monthly_cpf_interest(self, year=None):
        """Calculates CPF interest earned for each month based on lowest balance of the month.
        
        Singapore CPF Rule:
        - Monthly interest = (Lowest Balance in Month) * (Annual Rate / 12)
        - Extra 1% on first $60k combined balances ($20k cap from OA).
        """
        self.ensure_one()
        if not self.is_cpf:
            raise UserError("This account is not a Singapore CPF account.")

        if not year:
            year = fields.Date.today().year

        rate = (self.interest_rate or 2.5) / 100.0
        monthly_rate = rate / 12.0

        monthly_breakdown = []
        total_interest = 0.0

        for month in range(1, 13):
            start_date = date(year, month, 1)
            next_month = start_date + relativedelta(months=1)
            end_date = next_month - relativedelta(days=1)

            # Find all transactions up to end_date
            txs_in_month = self.env['moneta.transaction'].search([
                ('account_id', '=', self.id),
                ('transaction_date', '>=', start_date),
                ('transaction_date', '<=', end_date),
                ('state', '!=', 'void'),
            ], order='transaction_date asc, id asc')

            # Calculate balance at start of month
            txs_before = self.env['moneta.transaction'].search([
                ('account_id', '=', self.id),
                ('transaction_date', '<', start_date),
                ('state', '!=', 'void'),
            ])
            start_bal = self.opening_balance + sum(txs_before.mapped('amount'))

            lowest_bal = start_bal
            cur_bal = start_bal
            for tx in txs_in_month:
                cur_bal += tx.amount
                if cur_bal < lowest_bal:
                    lowest_bal = cur_bal

            lowest_bal = max(lowest_bal, 0.0)
            month_interest = round(lowest_bal * monthly_rate, 2)
            total_interest += month_interest

            monthly_breakdown.append({
                'month': start_date.strftime('%B %Y'),
                'start_balance': round(start_bal, 2),
                'lowest_balance': round(lowest_bal, 2),
                'closing_balance': round(cur_bal, 2),
                'interest_earned': month_interest,
            })

        return {
            'account_id': self.id,
            'account_name': self.name,
            'year': year,
            'annual_rate_pct': self.interest_rate,
            'total_annual_interest': round(total_interest, 2),
            'monthly_breakdown': monthly_breakdown,
        }


class MonetaCPFLifeSimulator(models.Model):
    _name = 'moneta.cpf.life.simulator'
    _description = 'Singapore CPF LIFE Retirement Payout Simulator'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Simulation Name', required=True, default='CPF LIFE Payout Simulation')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    birth_year = fields.Integer(string='Birth Year', default=1975, required=True)
    current_age = fields.Integer(string='Current Age', compute='_compute_current_age', store=True)
    ra_balance_at_55 = fields.Monetary(string='Projected RA Balance (at Age 55 / 65)', required=True, default=213000.0)

    # 2024 - 2026 CPF Retirement Sum Benchmarks
    brs_amount = fields.Monetary(string='Basic Retirement Sum (BRS)', default=106500.0)
    frs_amount = fields.Monetary(string='Full Retirement Sum (FRS)', default=213000.0)
    ers_amount = fields.Monetary(string='Enhanced Retirement Sum (ERS)', default=426000.0)

    plan_type = fields.Selection([
        ('standard', 'CPF LIFE Standard Plan (Level lifelong payouts)'),
        ('escalating', 'CPF LIFE Escalating Plan (+2% annual payout increase)'),
        ('basic', 'CPF LIFE Basic Plan (Lower payout, higher bequest)'),
    ], string='CPF LIFE Plan', default='standard', required=True)

    payout_start_age = fields.Selection([
        ('65', 'Age 65 (Standard Payout Eligibility Age)'),
        ('66', 'Age 66 (+7% payout bonus)'),
        ('67', 'Age 67 (+14% payout bonus)'),
        ('68', 'Age 68 (+21% payout bonus)'),
        ('69', 'Age 69 (+28% payout bonus)'),
        ('70', 'Age 70 (+35% maximum deferment bonus)'),
    ], string='Payout Start Age', default='65', required=True)

    # Computed simulation outputs
    retirement_sum_tier = fields.Selection([
        ('below_brs', 'Below Basic Retirement Sum (< BRS)'),
        ('brs', 'Basic Retirement Sum (BRS)'),
        ('frs', 'Full Retirement Sum (FRS)'),
        ('ers', 'Enhanced Retirement Sum (ERS)'),
        ('above_ers', 'Max Tier (Above ERS)'),
    ], string='Retirement Sum Tier', compute='_compute_simulation', store=True)

    monthly_payout_estimated = fields.Monetary(string='Est. Starting Monthly Payout', compute='_compute_simulation', store=True)
    annual_payout_estimated = fields.Monetary(string='Est. Starting Annual Payout', compute='_compute_simulation', store=True)
    payout_at_80 = fields.Monetary(string='Monthly Payout at Age 80', compute='_compute_simulation', store=True)
    payout_at_90 = fields.Monetary(string='Monthly Payout at Age 90', compute='_compute_simulation', store=True)

    cumulative_payout_85 = fields.Monetary(string='Total Cumulative Payout by Age 85', compute='_compute_simulation', store=True)
    cumulative_payout_95 = fields.Monetary(string='Total Cumulative Payout by Age 95', compute='_compute_simulation', store=True)
    estimated_bequest_75 = fields.Monetary(string='Est. Bequest to Beneficiaries at Age 75', compute='_compute_simulation', store=True)
    estimated_bequest_85 = fields.Monetary(string='Est. Bequest to Beneficiaries at Age 85', compute='_compute_simulation', store=True)

    notes = fields.Text(string='Retirement Notes & Strategy')

    @api.depends('birth_year')
    def _compute_current_age(self):
        current_year = fields.Date.today().year
        for rec in self:
            rec.current_age = max(current_year - (rec.birth_year or current_year), 0)

    @api.depends('ra_balance_at_55', 'plan_type', 'payout_start_age', 'brs_amount', 'frs_amount', 'ers_amount')
    def _compute_simulation(self):
        for rec in self:
            ra = rec.ra_balance_at_55 or 0.0
            start_age = int(rec.payout_start_age or 65)
            deferral_years = max(start_age - 65, 0)
            deferral_multiplier = 1.0 + (deferral_years * 0.07)  # ~7% increase per year of deferral

            # Determine retirement tier
            if ra < (rec.brs_amount or 106500.0):
                rec.retirement_sum_tier = 'below_brs'
            elif ra < (rec.frs_amount or 213000.0):
                rec.retirement_sum_tier = 'brs'
            elif ra < (rec.ers_amount or 426000.0):
                rec.retirement_sum_tier = 'frs'
            elif ra == (rec.ers_amount or 426000.0):
                rec.retirement_sum_tier = 'ers'
            else:
                rec.retirement_sum_tier = 'above_ers'

            # Base monthly payout factor: ~$1,650/mo per $213,000 FRS on Standard Plan at 65 (approx 0.00775 monthly ratio)
            base_ratio = 1650.0 / 213000.0

            if rec.plan_type == 'standard':
                # Level payout
                monthly = ra * base_ratio * deferral_multiplier
                rec.monthly_payout_estimated = round(monthly, 2)
                rec.annual_payout_estimated = round(monthly * 12.0, 2)
                rec.payout_at_80 = round(monthly, 2)
                rec.payout_at_90 = round(monthly, 2)

                # Total payouts
                years_to_85 = max(85 - start_age, 0)
                years_to_95 = max(95 - start_age, 0)
                rec.cumulative_payout_85 = round(monthly * 12.0 * years_to_85, 2)
                rec.cumulative_payout_95 = round(monthly * 12.0 * years_to_95, 2)

                # Bequest = RA balance + interest - payouts paid
                paid_at_75 = monthly * 12.0 * max(75 - start_age, 0)
                paid_at_85 = monthly * 12.0 * max(85 - start_age, 0)
                rec.estimated_bequest_75 = max(round(ra - paid_at_75, 2), 0.0)
                rec.estimated_bequest_85 = max(round(ra - paid_at_85, 2), 0.0)

            elif rec.plan_type == 'escalating':
                # Starting monthly is ~20% lower, but increases 2% every year
                monthly = ra * base_ratio * 0.80 * deferral_multiplier
                rec.monthly_payout_estimated = round(monthly, 2)
                rec.annual_payout_estimated = round(monthly * 12.0, 2)
                rec.payout_at_80 = round(monthly * ((1.02) ** (80 - start_age)), 2)
                rec.payout_at_90 = round(monthly * ((1.02) ** (90 - start_age)), 2)

                # Cumulative compounding
                cum_85 = sum(monthly * 12.0 * (1.02 ** y) for y in range(max(85 - start_age, 0)))
                cum_95 = sum(monthly * 12.0 * (1.02 ** y) for y in range(max(95 - start_age, 0)))
                rec.cumulative_payout_85 = round(cum_85, 2)
                rec.cumulative_payout_95 = round(cum_95, 2)

                paid_at_75 = sum(monthly * 12.0 * (1.02 ** y) for y in range(max(75 - start_age, 0)))
                paid_at_85 = cum_85
                rec.estimated_bequest_75 = max(round(ra - paid_at_75, 2), 0.0)
                rec.estimated_bequest_85 = max(round(ra - paid_at_85, 2), 0.0)

            elif rec.plan_type == 'basic':
                # Basic plan: ~10% lower payout than Standard, higher bequest until 90
                monthly = ra * base_ratio * 0.90 * deferral_multiplier
                rec.monthly_payout_estimated = round(monthly, 2)
                rec.annual_payout_estimated = round(monthly * 12.0, 2)
                rec.payout_at_80 = round(monthly, 2)
                rec.payout_at_90 = round(monthly * 0.85, 2)

                years_to_85 = max(85 - start_age, 0)
                years_to_95 = max(95 - start_age, 0)
                rec.cumulative_payout_85 = round(monthly * 12.0 * years_to_85, 2)
                rec.cumulative_payout_95 = round(monthly * 12.0 * years_to_95, 2)

                paid_at_75 = monthly * 12.0 * max(75 - start_age, 0)
                paid_at_85 = monthly * 12.0 * max(85 - start_age, 0)
                rec.estimated_bequest_75 = max(round((ra * 1.15) - paid_at_75, 2), 0.0)
                rec.estimated_bequest_85 = max(round((ra * 1.10) - paid_at_85, 2), 0.0)
