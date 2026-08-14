# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaLoanScenario(models.Model):
    _name = 'moneta.loan.scenario'
    _description = 'Moneta Loan & Mortgage Scenario'
    _order = 'name asc'

    name = fields.Char(string='Scenario Name', required=True)
    account_id = fields.Many2one(
        'moneta.account', string='Linked Loan Account',
        domain="[('account_type', 'in', ('loan', 'mortgage', 'loc'))]",
    )
    user_id = fields.Many2one(
        'res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True,
    )

    # Loan Inputs
    principal_amount = fields.Monetary(string='Principal Amount', required=True, default=300000.0)
    annual_interest_rate = fields.Float(string='Annual Interest Rate (%)', required=True, default=5.5, digits=(5, 3))
    loan_term_years = fields.Integer(string='Loan Term (Years)', required=True, default=30)
    loan_term_months = fields.Integer(string='Loan Term (Months)', compute='_compute_term_months', store=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)

    # Prepayment / Extra Payment Inputs
    extra_monthly_payment = fields.Monetary(string='Extra Monthly Principal', default=0.0)
    lump_sum_payment = fields.Monetary(string='Lump Sum Prepayment', default=0.0)
    lump_sum_date = fields.Date(string='Lump Sum Date')

    # Calculated Loan Metrics
    monthly_payment = fields.Monetary(string='Base Monthly Payment (P&I)', compute='_compute_amortization_schedule', store=True)
    total_payment_original = fields.Monetary(string='Original Total Cost', compute='_compute_amortization_schedule', store=True)
    total_interest_original = fields.Monetary(string='Original Total Interest', compute='_compute_amortization_schedule', store=True)
    original_payoff_date = fields.Date(string='Original Payoff Date', compute='_compute_amortization_schedule', store=True)

    # Accelerated Payoff Metrics
    total_payment_actual = fields.Monetary(string='Accelerated Total Cost', compute='_compute_amortization_schedule', store=True)
    total_interest_actual = fields.Monetary(string='Accelerated Total Interest', compute='_compute_amortization_schedule', store=True)
    actual_payoff_date = fields.Date(string='Accelerated Payoff Date', compute='_compute_amortization_schedule', store=True)
    interest_saved = fields.Monetary(string='Total Interest Saved', compute='_compute_amortization_schedule', store=True)
    months_saved = fields.Integer(string='Months Saved', compute='_compute_amortization_schedule', store=True)
    years_saved = fields.Float(string='Years Saved', compute='_compute_amortization_schedule', digits=(5, 1), store=True)

    # Schedule Lines & Rate Changes
    line_ids = fields.One2many('moneta.loan.amortization.line', 'scenario_id', string='Amortization Schedule')
    rate_change_ids = fields.One2many('moneta.loan.rate.change', 'scenario_id', string='Rate Changes')

    @api.depends('loan_term_years')
    def _compute_term_months(self):
        for rec in self:
            rec.loan_term_months = (rec.loan_term_years or 0) * 12

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            bal = abs(float(self.account_id.current_balance or 0.0))
            if bal > 0:
                self.principal_amount = bal
            if self.account_id.currency_id:
                self.currency_id = self.account_id.currency_id

    @api.depends('principal_amount', 'annual_interest_rate', 'loan_term_years', 'start_date',
                 'extra_monthly_payment', 'lump_sum_payment', 'lump_sum_date', 'rate_change_ids.effective_date', 'rate_change_ids.annual_rate')
    def _compute_amortization_schedule(self):
        for rec in self:
            P = float(rec.principal_amount or 0.0)
            annual_rate = float(rec.annual_interest_rate or 0.0) / 100.0
            n_months = int(rec.loan_term_months or 360)
            start = rec.start_date or fields.Date.context_today(rec)

            if P <= 0 or n_months <= 0:
                rec.monthly_payment = 0.0
                rec.total_payment_original = 0.0
                rec.total_interest_original = 0.0
                rec.original_payoff_date = start
                rec.total_payment_actual = 0.0
                rec.total_interest_actual = 0.0
                rec.actual_payoff_date = start
                rec.interest_saved = 0.0
                rec.months_saved = 0
                rec.years_saved = 0.0
                continue

            # Standard Annuity Monthly Payment formula: PMT = P * [r(1+r)^n] / [(1+r)^n - 1]
            r = annual_rate / 12.0
            if r > 0:
                pmt = P * (r * ((1 + r) ** n_months)) / (((1 + r) ** n_months) - 1)
            else:
                pmt = P / n_months

            rec.monthly_payment = round(pmt, 4)

            # 1. Compute Original baseline schedule
            orig_balance = P
            orig_interest_sum = 0.0
            for m in range(1, n_months + 1):
                interest = orig_balance * r
                principal = min(pmt - interest, orig_balance)
                orig_interest_sum += interest
                orig_balance -= principal
                if orig_balance <= 0.0001:
                    break

            rec.total_interest_original = round(orig_interest_sum, 4)
            rec.total_payment_original = round(P + orig_interest_sum, 4)
            rec.original_payoff_date = start + relativedelta(months=n_months)

            # 2. Compute Accelerated schedule with prepayments
            extra_m = float(rec.extra_monthly_payment or 0.0)
            lump_amt = float(rec.lump_sum_payment or 0.0)
            lump_dt = rec.lump_sum_date

            curr_balance = P
            actual_interest_sum = 0.0
            actual_months = 0
            cur_date = start

            # Build rate change map
            rate_changes = sorted(rec.rate_change_ids, key=lambda rc: rc.effective_date or start)

            while curr_balance > 0.0001 and actual_months < 1200:
                actual_months += 1
                cur_date = start + relativedelta(months=actual_months - 1)

                # Check dynamic rate
                cur_r = r
                for rc in rate_changes:
                    if rc.effective_date and cur_date >= rc.effective_date:
                        cur_r = (float(rc.annual_rate or 0.0) / 100.0) / 12.0

                interest = curr_balance * cur_r
                principal = pmt - interest

                # Apply lump sum if applicable this month
                lump_this_month = 0.0
                if lump_dt and lump_amt > 0:
                    if cur_date.year == lump_dt.year and cur_date.month == lump_dt.month:
                        lump_this_month = lump_amt

                total_principal = principal + extra_m + lump_this_month
                if total_principal > curr_balance:
                    total_principal = curr_balance

                actual_interest_sum += interest
                curr_balance -= total_principal

            rec.total_interest_actual = round(actual_interest_sum, 4)
            rec.total_payment_actual = round(P + actual_interest_sum, 4)
            rec.actual_payoff_date = cur_date
            rec.interest_saved = round(max(orig_interest_sum - actual_interest_sum, 0.0), 4)
            rec.months_saved = max(n_months - actual_months, 0)
            rec.years_saved = round(rec.months_saved / 12.0, 1)

    def action_generate_schedule(self):
        """Populate the One2many line table with full month-by-month amortization."""
        self.ensure_one()
        self.line_ids.unlink()

        P = float(self.principal_amount or 0.0)
        annual_rate = float(self.annual_interest_rate or 0.0) / 100.0
        n_months = int(self.loan_term_months or 360)
        start = self.start_date or fields.Date.context_today(self)
        extra_m = float(self.extra_monthly_payment or 0.0)
        lump_amt = float(self.lump_sum_payment or 0.0)
        lump_dt = self.lump_sum_date

        r = annual_rate / 12.0
        pmt = float(self.monthly_payment or 0.0)
        if pmt <= 0:
            return

        rate_changes = sorted(self.rate_change_ids, key=lambda rc: rc.effective_date or start)

        lines = []
        curr_balance = P
        month_idx = 0

        while curr_balance > 0.0001 and month_idx < 1200:
            month_idx += 1
            cur_date = start + relativedelta(months=month_idx - 1)

            cur_r = r
            for rc in rate_changes:
                if rc.effective_date and cur_date >= rc.effective_date:
                    cur_r = (float(rc.annual_rate or 0.0) / 100.0) / 12.0

            interest = curr_balance * cur_r
            sched_principal = min(pmt - interest, curr_balance)

            lump_this_month = 0.0
            if lump_dt and lump_amt > 0:
                if cur_date.year == lump_dt.year and cur_date.month == lump_dt.month:
                    lump_this_month = lump_amt

            extra_total = extra_m + lump_this_month
            if (sched_principal + extra_total) > curr_balance:
                extra_total = max(curr_balance - sched_principal, 0.0)

            total_principal = sched_principal + extra_total
            end_balance = max(curr_balance - total_principal, 0.0)

            lines.append({
                'scenario_id': self.id,
                'payment_number': month_idx,
                'payment_date': cur_date,
                'starting_balance': round(curr_balance, 4),
                'scheduled_payment': round(sched_principal + interest, 4),
                'principal_amount': round(sched_principal, 4),
                'interest_amount': round(interest, 4),
                'extra_payment': round(extra_total, 4),
                'total_payment': round(sched_principal + interest + extra_total, 4),
                'ending_balance': round(end_balance, 4),
                'currency_id': self.currency_id.id,
            })
            curr_balance = end_balance

        self.env['moneta.loan.amortization.line'].create(lines)
        return True


class MonetaLoanAmortizationLine(models.Model):
    _name = 'moneta.loan.amortization.line'
    _description = 'Moneta Loan Amortization Schedule Line'
    _order = 'payment_number asc'

    scenario_id = fields.Many2one('moneta.loan.scenario', string='Loan Scenario', ondelete='cascade', required=True)
    currency_id = fields.Many2one('res.currency', related='scenario_id.currency_id', store=True, readonly=True)
    user_id = fields.Many2one('res.users', related='scenario_id.user_id', store=True, index=True)

    payment_number = fields.Integer(string='#', required=True)
    payment_date = fields.Date(string='Payment Date', required=True)
    starting_balance = fields.Monetary(string='Starting Balance')
    scheduled_payment = fields.Monetary(string='Payment')
    principal_amount = fields.Monetary(string='Principal')
    interest_amount = fields.Monetary(string='Interest')
    extra_payment = fields.Monetary(string='Extra Payment')
    total_payment = fields.Monetary(string='Total Paid')
    ending_balance = fields.Monetary(string='Ending Balance')


class MonetaLoanRateChange(models.Model):
    _name = 'moneta.loan.rate.change'
    _description = 'Moneta Variable Loan Rate Adjustment'
    _order = 'effective_date asc'

    scenario_id = fields.Many2one('moneta.loan.scenario', string='Loan Scenario', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', related='scenario_id.user_id', store=True, index=True)
    effective_date = fields.Date(string='Effective Date', required=True)
    annual_rate = fields.Float(string='New Annual Rate (%)', required=True, digits=(5, 3))
    note = fields.Char(string='Adjustment Note')
