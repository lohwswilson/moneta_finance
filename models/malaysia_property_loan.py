# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api


class MonetaMalaysiaFlexiLoan(models.Model):
    _name = 'moneta.malaysia.flexi.loan'
    _description = 'Malaysia Semi-Flexi / Full-Flexi Home Loan & SBR Simulator'
    _order = 'name asc'

    name = fields.Char(string='Loan Description', required=True)
    property_id = fields.Many2one('moneta.property', string='Mortgaged Property', domain="[('asset_category', '=', 'real_estate')]")
    user_id = fields.Many2one('res.users', string='Borrower', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.MYR', raise_if_not_found=False) or self.env.company.currency_id, required=True)

    loan_type = fields.Selection([
        ('full_flexi', 'Full-Flexi Home Loan (Linked Current Account)'),
        ('semi_flexi', 'Semi-Flexi Home Loan (Advance Payment / Withdrawal Fee)'),
        ('conventional_term', 'Conventional Term Loan (Fixed Repayment)'),
        ('islamic_flexi', 'Islamic Home Financing (Commodity Murabahah)'),
    ], string='Loan Facility Type', default='full_flexi', required=True)

    lending_bank = fields.Char(string='Financier / Bank', help='e.g. Maybank, CIMB, Public Bank, Hong Leong, RHB')
    original_loan_amount = fields.Monetary(string='Original Loan Amount', required=True, default=500000.0)
    outstanding_principal = fields.Monetary(string='Outstanding Principal Balance', required=True, default=450000.0)
    loan_tenure_years = fields.Integer(string='Loan Tenure (Years)', default=30, required=True)

    # Standardised Base Rate (SBR) & Spread
    standardised_base_rate = fields.Float(string='Standardised Base Rate / SBR (%)', default=3.00, digits=(4, 2))
    bank_spread_rate = fields.Float(string='Bank Spread (%)', default=1.15, digits=(4, 2))
    effective_interest_rate = fields.Float(string='Effective Interest Rate (%)', compute='_compute_rates', store=True, digits=(4, 2))

    monthly_installment = fields.Monetary(string='Standard Monthly Installment', compute='_compute_rates', store=True)

    # Flexi Offset Account Balance
    flexi_deposit_balance = fields.Monetary(
        string='Spare Cash Parked in Flexi Current Account',
        help='Cash kept in the linked flexi account offsets the loan principal on a daily basis to reduce interest charged.',
        default=50000.0,
    )
    net_chargeable_principal = fields.Monetary(
        string='Net Principal Subject to Interest',
        compute='_compute_flexi_savings',
        store=True,
    )
    annual_interest_without_flexi = fields.Monetary(
        string='Annual Interest (Without Flexi Offset)',
        compute='_compute_flexi_savings',
        store=True,
    )
    annual_interest_with_flexi = fields.Monetary(
        string='Annual Interest (With Flexi Offset)',
        compute='_compute_flexi_savings',
        store=True,
    )
    annual_interest_saved = fields.Monetary(
        string='Annual Interest Saved ($ / RM)',
        compute='_compute_flexi_savings',
        store=True,
    )
    flexi_return_equivalent_pct = fields.Float(
        string='Risk-Free Tax-Free Equivalent Yield (%)',
        compute='_compute_flexi_savings',
        store=True,
        digits=(4, 2),
    )

    notes = fields.Text(string='Loan Terms & Package Details')

    @api.depends('standardised_base_rate', 'bank_spread_rate', 'outstanding_principal', 'loan_tenure_years')
    def _compute_rates(self):
        for rec in self:
            eff_rate = float(rec.standardised_base_rate or 3.0) + float(rec.bank_spread_rate or 1.15)
            rec.effective_interest_rate = round(eff_rate, 2)

            # Monthly installment amortization formula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
            p = float(rec.outstanding_principal or 0.0)
            r = (eff_rate / 100.0) / 12.0
            n = (rec.loan_tenure_years or 30) * 12
            if p > 0 and r > 0 and n > 0:
                m = p * (r * ((1.0 + r) ** n)) / (((1.0 + r) ** n) - 1.0)
                rec.monthly_installment = round(m, 2)
            else:
                rec.monthly_installment = 0.0

    @api.depends('outstanding_principal', 'flexi_deposit_balance', 'effective_interest_rate')
    def _compute_flexi_savings(self):
        for rec in self:
            p = float(rec.outstanding_principal or 0.0)
            dep = float(rec.flexi_deposit_balance or 0.0)
            rate = float(rec.effective_interest_rate or 0.0) / 100.0

            net_p = max(p - dep, 0.0)
            rec.net_chargeable_principal = round(net_p, 2)

            int_no_flexi = p * rate
            int_with_flexi = net_p * rate
            saved = int_no_flexi - int_with_flexi

            rec.annual_interest_without_flexi = round(int_no_flexi, 2)
            rec.annual_interest_with_flexi = round(int_with_flexi, 2)
            rec.annual_interest_saved = round(saved, 2)
            rec.flexi_return_equivalent_pct = rec.effective_interest_rate


class MonetaRpgtCalculator(models.Model):
    _name = 'moneta.rpgt.calculator'
    _description = 'Malaysia Real Property Gains Tax (RPGT) Calculator'
    _order = 'disposal_date desc, id desc'

    name = fields.Char(string='RPGT Calculation Name', compute='_compute_name', store=True)
    property_id = fields.Many2one('moneta.property', string='Property Disposed', domain="[('asset_category', '=', 'real_estate')]")
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.MYR', raise_if_not_found=False) or self.env.company.currency_id, required=True)

    citizenship_status = fields.Selection([
        ('citizen_pr', 'Malaysian Citizen / Permanent Resident (PR)'),
        ('foreigner', 'Non-Citizen / Foreigner'),
        ('company', 'Malaysian Company'),
    ], string='Seller Citizenship Status', default='citizen_pr', required=True)

    acquisition_date = fields.Date(string='Acquisition Date (SPA Date)', required=True)
    disposal_date = fields.Date(string='Disposal Date (SPA Date)', required=True, default=fields.Date.context_today)

    acquisition_price = fields.Monetary(string='Acquisition Price', required=True, default=0.0)
    disposal_price = fields.Monetary(string='Disposal / Sale Price', required=True, default=0.0)

    # Allowable Expenses (Incidental Costs & Renovation)
    allowable_expenses = fields.Monetary(
        string='Allowable Expenses (Legal Fees, Stamp Duty, Renovation)',
        help='Legal fees, agent commission, stamp duty, valuer fees, and capital enhancement/renovations.',
        default=0.0,
    )

    holding_period_years = fields.Float(string='Holding Period (Years)', compute='_compute_rpgt', store=True, digits=(4, 1))
    gross_chargeable_gain = fields.Monetary(string='Gross Capital Gain', compute='_compute_rpgt', store=True)
    
    # Exemption
    is_once_in_lifetime_exemption = fields.Boolean(
        string='Apply Once-in-a-Lifetime Private Residence Exemption (Section 8)',
        default=False,
        help='Section 8 exemption for Malaysian citizens on disposal of one private residential property.',
    )
    individual_exemption_amount = fields.Monetary(
        string='Statutory Exemption (10% of gain or RM10,000)',
        compute='_compute_rpgt',
        store=True,
    )
    net_chargeable_gain = fields.Monetary(string='Net Chargeable Gain', compute='_compute_rpgt', store=True)

    rpgt_rate_pct = fields.Float(string='Applicable RPGT Rate (%)', compute='_compute_rpgt', store=True, digits=(4, 1))
    rpgt_tax_payable = fields.Monetary(string='RPGT Tax Payable', compute='_compute_rpgt', store=True)

    @api.depends('property_id.name', 'disposal_date')
    def _compute_name(self):
        for rec in self:
            p_name = rec.property_id.name if rec.property_id else 'Property'
            rec.name = f"RPGT Assessment: {p_name} ({rec.disposal_date or 'Draft'})"

    @api.depends(
        'acquisition_date', 'disposal_date', 'acquisition_price', 'disposal_price',
        'allowable_expenses', 'citizenship_status', 'is_once_in_lifetime_exemption'
    )
    def _compute_rpgt(self):
        for rec in self:
            if not rec.acquisition_date or not rec.disposal_date:
                rec.holding_period_years = 0.0
                rec.gross_chargeable_gain = 0.0
                rec.individual_exemption_amount = 0.0
                rec.net_chargeable_gain = 0.0
                rec.rpgt_rate_pct = 0.0
                rec.rpgt_tax_payable = 0.0
                continue

            days = (rec.disposal_date - rec.acquisition_date).days
            years = max(days / 365.25, 0.0)
            rec.holding_period_years = round(years, 1)

            # Gross Gain = Disposal Price - (Acquisition Price + Allowable Expenses)
            acq_cost = float(rec.acquisition_price or 0.0) + float(rec.allowable_expenses or 0.0)
            disp_price = float(rec.disposal_price or 0.0)
            gross_gain = max(disp_price - acq_cost, 0.0)
            rec.gross_chargeable_gain = round(gross_gain, 2)

            # RPGT Rates (Budget 2022 onwards)
            # Citizen/PR:
            # <= 3 years: 30%
            # 4th year: 20%
            # 5th year: 15%
            # > 5 years (6th year onwards): 0%
            # Foreigner:
            # <= 5 years: 30%
            # > 5 years: 10%
            # Company:
            # <= 3 years: 30%
            # 4th year: 20%
            # 5th year: 15%
            # > 5 years: 10%
            rate = 0.0
            if rec.citizenship_status == 'citizen_pr':
                if years <= 3.0:
                    rate = 30.0
                elif years <= 4.0:
                    rate = 20.0
                elif years <= 5.0:
                    rate = 15.0
                else:
                    rate = 0.0
            elif rec.citizenship_status == 'foreigner':
                if years <= 5.0:
                    rate = 30.0
                else:
                    rate = 10.0
            else:  # Company
                if years <= 3.0:
                    rate = 30.0
                elif years <= 4.0:
                    rate = 20.0
                elif years <= 5.0:
                    rate = 15.0
                else:
                    rate = 10.0

            rec.rpgt_rate_pct = rate

            if rec.is_once_in_lifetime_exemption:
                rec.individual_exemption_amount = gross_gain
                rec.net_chargeable_gain = 0.0
                rec.rpgt_tax_payable = 0.0
            else:
                # Individual exemption: 10% of profit or RM10,000 (whichever is higher)
                exemption = max(gross_gain * 0.10, 10000.0) if (gross_gain > 0 and rec.citizenship_status == 'citizen_pr') else 0.0
                exemption = min(exemption, gross_gain)
                rec.individual_exemption_amount = round(exemption, 2)
                
                net_gain = max(gross_gain - exemption, 0.0)
                rec.net_chargeable_gain = round(net_gain, 2)
                rec.rpgt_tax_payable = round(net_gain * (rate / 100.0), 2)
