# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class MonetaPropertySingapore(models.Model):
    _inherit = 'moneta.property'

    is_singapore_property = fields.Boolean(string='Is Singapore Property', default=False)
    singapore_housing_type = fields.Selection([
        ('hdb_bto', 'HDB Build-To-Order (BTO)'),
        ('hdb_resale', 'HDB Resale Flat'),
        ('ec', 'Executive Condominium (EC)'),
        ('private_condo', 'Private Condominium / Apartment'),
        ('landed', 'Landed Property (Terrace/Semi-D/Bungalow)'),
        ('commercial', 'Commercial / Shophouse'),
    ], string='Singapore Property Type', default='hdb_resale')

    # CPF Housing Withdrawal & Accrued Interest Tracking
    cpf_downpayment_amount = fields.Monetary(string='CPF OA Downpayment Used', default=0.0)
    cpf_monthly_instalment = fields.Monetary(string='Monthly CPF OA Mortgage Deduction', default=0.0)
    cpf_housing_grants = fields.Monetary(string='CPF Housing Grants Received (EHG/PHG)', default=0.0)
    cpf_holding_years = fields.Float(string='Holding Period (Years)', compute='_compute_cpf_holding_years', store=True, digits=(5, 1))

    cpf_principal_withdrawn = fields.Monetary(string='Total CPF Principal Withdrawn', compute='_compute_cpf_accrued_interest', store=True)
    cpf_accrued_interest = fields.Monetary(string='CPF Accrued Interest (2.5% Compounded)', compute='_compute_cpf_accrued_interest', store=True)
    total_cpf_refund_due = fields.Monetary(string='Total CPF Refund Due Upon Sale', compute='_compute_cpf_accrued_interest', store=True)
    projected_net_cash_proceeds = fields.Monetary(string='Projected Net Cash Proceeds Upon Sale', compute='_compute_cpf_accrued_interest', store=True)

    @api.depends('purchase_date')
    def _compute_cpf_holding_years(self):
        today = fields.Date.today()
        for rec in self:
            if rec.purchase_date:
                diff_days = (today - rec.purchase_date).days
                rec.cpf_holding_years = max(round(diff_days / 365.25, 1), 0.0)
            else:
                rec.cpf_holding_years = 0.0

    @api.depends('is_singapore_property', 'cpf_downpayment_amount', 'cpf_monthly_instalment',
                 'cpf_housing_grants', 'cpf_holding_years', 'current_market_value', 'mortgage_balance')
    def _compute_cpf_accrued_interest(self):
        rate = 0.025  # Singapore CPF OA rate: 2.50% p.a.
        for rec in self:
            if not rec.is_singapore_property:
                rec.cpf_principal_withdrawn = 0.0
                rec.cpf_accrued_interest = 0.0
                rec.total_cpf_refund_due = 0.0
                rec.projected_net_cash_proceeds = 0.0
                continue

            years = rec.cpf_holding_years or 0.0
            downpayment = rec.cpf_downpayment_amount or 0.0
            grants = rec.cpf_housing_grants or 0.0
            monthly = rec.cpf_monthly_instalment or 0.0

            total_monthly_principal = monthly * 12.0 * years
            principal = downpayment + grants + total_monthly_principal
            rec.cpf_principal_withdrawn = round(principal, 2)

            # Compounding calculation
            # 1. Lump sums (downpayment + grants) compounded over 'years':
            compounded_lump = (downpayment + grants) * ((1.0 + rate) ** years)

            # 2. Annuity of monthly payments over 'years':
            # Future Value of monthly stream = monthly * [((1 + rate/12)^(months) - 1) / (rate/12)]
            months = int(years * 12)
            r_m = rate / 12.0
            if months > 0 and r_m > 0:
                fv_stream = monthly * (((1.0 + r_m) ** months - 1.0) / r_m)
            else:
                fv_stream = 0.0

            total_fv = compounded_lump + fv_stream
            accrued = max(total_fv - principal, 0.0)
            rec.cpf_accrued_interest = round(accrued, 2)
            rec.total_cpf_refund_due = round(principal + accrued, 2)

            # Net Cash Proceeds = Market Value - Outstanding Mortgage - CPF Refund
            mv = rec.current_market_value or 0.0
            debt = rec.mortgage_balance or 0.0
            rec.projected_net_cash_proceeds = round(mv - debt - rec.total_cpf_refund_due, 2)


class MonetaCPFAccruedInterestSimulator(models.Model):
    _name = 'moneta.cpf.accrued.interest'
    _description = 'Singapore CPF Housing Accrued Interest & Sale Proceeds Simulator'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Simulation Title', required=True, default='CPF Accrued Interest Simulation')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    property_name = fields.Char(string='Property Description', default='4-Room Resale Flat')
    property_id = fields.Many2one('moneta.property', string='Linked Property (Optional)', domain="[('is_singapore_property', '=', True)]")

    # Financial Inputs
    purchase_price = fields.Monetary(string='Original Purchase Price', required=True, default=600000.0)
    cpf_downpayment = fields.Monetary(string='CPF OA Downpayment Used', required=True, default=120000.0)
    cpf_grants = fields.Monetary(string='CPF Housing Grants Received (EHG/PHG/Family)', default=50000.0)
    monthly_cpf_payment = fields.Monetary(string='Monthly CPF OA Mortgage Deduction', required=True, default=1500.0)
    holding_period_years = fields.Float(string='Simulated Holding Period (Years)', required=True, default=10.0)

    projected_selling_price = fields.Monetary(string='Expected Selling Price', required=True, default=850000.0)
    outstanding_loan_balance = fields.Monetary(string='Estimated Remaining Loan Balance', required=True, default=280000.0)
    estimated_resale_fees = fields.Monetary(string='Agent Commission & Legal Fees (~2.5%)', default=21250.0)

    # Computed Outputs
    total_cpf_principal = fields.Monetary(string='Total CPF Principal Withdrawn', compute='_compute_accrued_simulation', store=True)
    total_cpf_accrued_interest = fields.Monetary(string='CPF Accrued Interest (2.5% Compounded)', compute='_compute_accrued_simulation', store=True)
    total_cpf_refund_to_oa = fields.Monetary(string='Total Refund Due to CPF OA', compute='_compute_accrued_simulation', store=True)
    
    gross_sales_proceeds = fields.Monetary(string='Gross Selling Price', compute='_compute_accrued_simulation', store=True)
    net_cash_in_hand = fields.Monetary(string='Estimated Net Cash in Hand ($)', compute='_compute_accrued_simulation', store=True)
    is_negative_cash_sale = fields.Boolean(string='Negative Cash Sale Warning', compute='_compute_accrued_simulation', store=True)

    notes = fields.Text(string='Strategy Notes')

    @api.onchange('property_id')
    def _onchange_property_id(self):
        if self.property_id:
            self.property_name = self.property_id.name
            self.purchase_price = self.property_id.purchase_price or 600000.0
            self.cpf_downpayment = self.property_id.cpf_downpayment_amount or 0.0
            self.cpf_grants = self.property_id.cpf_housing_grants or 0.0
            self.monthly_cpf_payment = self.property_id.cpf_monthly_instalment or 0.0
            self.holding_period_years = self.property_id.cpf_holding_years or 5.0
            self.projected_selling_price = self.property_id.current_market_value or 750000.0
            self.outstanding_loan_balance = self.property_id.mortgage_balance or 0.0

    @api.depends('cpf_downpayment', 'cpf_grants', 'monthly_cpf_payment', 'holding_period_years',
                 'projected_selling_price', 'outstanding_loan_balance', 'estimated_resale_fees')
    def _compute_accrued_simulation(self):
        rate = 0.025
        for rec in self:
            years = rec.holding_period_years or 0.0
            down = rec.cpf_downpayment or 0.0
            grants = rec.cpf_grants or 0.0
            monthly = rec.monthly_cpf_payment or 0.0

            total_stream_prin = monthly * 12.0 * years
            prin = down + grants + total_stream_prin
            rec.total_cpf_principal = round(prin, 2)

            comp_lump = (down + grants) * ((1.0 + rate) ** years)
            months = int(years * 12)
            r_m = rate / 12.0
            fv_stream = monthly * (((1.0 + r_m) ** months - 1.0) / r_m) if months > 0 and r_m > 0 else 0.0

            total_fv = comp_lump + fv_stream
            accrued = max(total_fv - prin, 0.0)
            rec.total_cpf_accrued_interest = round(accrued, 2)
            rec.total_cpf_refund_to_oa = round(prin + accrued, 2)

            sell_p = rec.projected_selling_price or 0.0
            rec.gross_sales_proceeds = sell_p
            loan = rec.outstanding_loan_balance or 0.0
            fees = rec.estimated_resale_fees or 0.0

            net = sell_p - loan - rec.total_cpf_refund_to_oa - fees
            rec.net_cash_in_hand = round(net, 2)
            rec.is_negative_cash_sale = bool(net < 0.0)


class MonetaSingaporePropertyAffordability(models.Model):
    _name = 'moneta.singapore.property.affordability'
    _description = 'Singapore Property Stamp Duty (BSD/ABSD), TDSR/MSR & Mortgage Comparator'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Affordability Assessment', required=True, default='Singapore Property Affordability Assessment')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    property_price = fields.Monetary(string='Purchase Property Price ($)', required=True, default=1200000.0)
    property_type = fields.Selection([
        ('residential', 'Residential Property (HDB / Condo / Landed)'),
        ('commercial', 'Commercial / Industrial Property'),
    ], string='Property Class', default='residential', required=True)

    buyer_profile = fields.Selection([
        ('sc_first', 'Singapore Citizen (1st Property)'),
        ('sc_second', 'Singapore Citizen (2nd Property)'),
        ('sc_third', 'Singapore Citizen (3rd+ Property)'),
        ('spr_first', 'Singapore PR (1st Property)'),
        ('spr_second', 'Singapore PR (2nd Property)'),
        ('spr_third', 'Singapore PR (3rd+ Property)'),
        ('foreigner', 'Foreigner (Any Property)'),
        ('entity', 'Entity / Corporate / Trust'),
    ], string='Buyer Residency & Count Profile', default='sc_first', required=True)

    # Stamp Duty Calculations
    bsd_amount = fields.Monetary(string="Buyer's Stamp Duty (BSD)", compute='_compute_stamp_duties', store=True)
    absd_rate_pct = fields.Float(string='ABSD Rate (%)', compute='_compute_stamp_duties', store=True)
    absd_amount = fields.Monetary(string="Additional Buyer's Stamp Duty (ABSD)", compute='_compute_stamp_duties', store=True)
    total_stamp_duty = fields.Monetary(string='Total Stamp Duty Payable', compute='_compute_stamp_duties', store=True)

    # Income & Debt Parameters for TDSR & MSR
    gross_monthly_income = fields.Monetary(string='Gross Monthly Household Income', required=True, default=15000.0)
    other_monthly_debt_commitments = fields.Monetary(string='Other Monthly Debt (Car, Cards, Loans)', default=1200.0)
    loan_tenure_years = fields.Integer(string='Loan Tenure (Years)', default=25, required=True)

    # Mortgage Rate Packages for Comparison
    hdb_loan_rate = fields.Float(string='HDB Concessionary Rate (%)', default=2.60, digits=(5, 2))
    bank_sora_rate = fields.Float(string='Bank SORA Mortgage Rate (%)', default=3.20, digits=(5, 2))
    stress_test_rate = fields.Float(string='MAS Regulatory Stress-Test Rate (%)', default=4.00, digits=(5, 2))

    # Affordability Limits
    tdsr_limit_pct = fields.Float(string='TDSR Regulatory Limit (%)', default=55.0)
    msr_limit_pct = fields.Float(string='MSR Limit for HDB/EC (%)', default=30.0)

    max_monthly_tdsr_allowance = fields.Monetary(string='Max Monthly Debt Allowed by TDSR (55%)', compute='_compute_affordability', store=True)
    max_monthly_msr_allowance = fields.Monetary(string='Max Monthly Mortgage Allowed by MSR (30%)', compute='_compute_affordability', store=True)
    
    simulated_monthly_mortgage_hdb = fields.Monetary(string='Monthly Payment (HDB 2.60%)', compute='_compute_affordability', store=True)
    simulated_monthly_mortgage_bank = fields.Monetary(string='Monthly Payment (Bank SORA)', compute='_compute_affordability', store=True)
    simulated_monthly_mortgage_stress = fields.Monetary(string='Monthly Payment (MAS 4.0% Stress Test)', compute='_compute_affordability', store=True)

    tdsr_actual_pct = fields.Float(string='Actual TDSR Ratio (%)', compute='_compute_affordability', store=True, digits=(5, 2))
    msr_actual_pct = fields.Float(string='Actual MSR Ratio (%)', compute='_compute_affordability', store=True, digits=(5, 2))

    tdsr_passed = fields.Boolean(string='TDSR Compliant (<= 55%)', compute='_compute_affordability', store=True)
    msr_passed = fields.Boolean(string='MSR Compliant (<= 30%)', compute='_compute_affordability', store=True)

    notes = fields.Text(string='Affordability & Financing Strategy Notes')

    @api.depends('property_price', 'property_type', 'buyer_profile')
    def _compute_stamp_duties(self):
        for rec in self:
            price = rec.property_price or 0.0
            
            # --- 1. Buyer's Stamp Duty (BSD) ---
            # Residential BSD Brackets:
            # 1st $180k @ 1%
            # Next $180k ($180k-$360k) @ 2%
            # Next $640k ($360k-$1.0m) @ 3%
            # Next $500k ($1.0m-$1.5m) @ 4%
            # Next $1.5m ($1.5m-$3.0m) @ 5%
            # Excess > $3.0m @ 6%
            bsd = 0.0
            rem = price

            tier1 = min(rem, 180000.0)
            bsd += tier1 * 0.01
            rem -= tier1

            tier2 = min(rem, 180000.0)
            bsd += tier2 * 0.02
            rem -= tier2

            tier3 = min(rem, 640000.0)
            bsd += tier3 * 0.03
            rem -= tier3

            tier4 = min(rem, 500000.0)
            bsd += tier4 * 0.04
            rem -= tier4

            tier5 = min(rem, 1500000.0)
            bsd += tier5 * 0.05
            rem -= tier5

            if rem > 0:
                bsd += rem * 0.06

            rec.bsd_amount = round(bsd, 2)

            # --- 2. Additional Buyer's Stamp Duty (ABSD) ---
            absd_rate = 0.0
            if rec.property_type == 'residential':
                if rec.buyer_profile == 'sc_first':
                    absd_rate = 0.0
                elif rec.buyer_profile == 'sc_second':
                    absd_rate = 20.0
                elif rec.buyer_profile == 'sc_third':
                    absd_rate = 30.0
                elif rec.buyer_profile == 'spr_first':
                    absd_rate = 5.0
                elif rec.buyer_profile == 'spr_second':
                    absd_rate = 30.0
                elif rec.buyer_profile == 'spr_third':
                    absd_rate = 35.0
                elif rec.buyer_profile == 'foreigner':
                    absd_rate = 60.0
                elif rec.buyer_profile == 'entity':
                    absd_rate = 65.0

            rec.absd_rate_pct = absd_rate
            rec.absd_amount = round(price * (absd_rate / 100.0), 2)
            rec.total_stamp_duty = round(rec.bsd_amount + rec.absd_amount, 2)

    @api.depends('property_price', 'gross_monthly_income', 'other_monthly_debt_commitments',
                 'loan_tenure_years', 'hdb_loan_rate', 'bank_sora_rate', 'stress_test_rate',
                 'tdsr_limit_pct', 'msr_limit_pct')
    def _compute_affordability(self):
        for rec in self:
            income = rec.gross_monthly_income or 0.0
            other_debt = rec.other_monthly_debt_commitments or 0.0
            price = rec.property_price or 0.0
            tenure_m = int((rec.loan_tenure_years or 25) * 12)

            # Max allowable debt payments
            rec.max_monthly_tdsr_allowance = round(income * ((rec.tdsr_limit_pct or 55.0) / 100.0), 2)
            rec.max_monthly_msr_allowance = round(income * ((rec.msr_limit_pct or 30.0) / 100.0), 2)

            # Assume 75% loan-to-value (LTV)
            loan_quantum = price * 0.75

            # Monthly payment helper
            def _calc_pmt(principal, annual_r, months):
                r = (annual_r / 100.0) / 12.0
                if r <= 0 or months <= 0:
                    return principal / max(months, 1)
                return principal * (r * ((1.0 + r) ** months)) / (((1.0 + r) ** months) - 1.0)

            hdb_pmt = _calc_pmt(loan_quantum, rec.hdb_loan_rate or 2.60, tenure_m)
            bank_pmt = _calc_pmt(loan_quantum, rec.bank_sora_rate or 3.20, tenure_m)
            stress_pmt = _calc_pmt(loan_quantum, rec.stress_test_rate or 4.00, tenure_m)

            rec.simulated_monthly_mortgage_hdb = round(hdb_pmt, 2)
            rec.simulated_monthly_mortgage_bank = round(bank_pmt, 2)
            rec.simulated_monthly_mortgage_stress = round(stress_pmt, 2)

            # Compliance check based on MAS stress-test rate
            total_debt_stress = stress_pmt + other_debt
            if income > 0:
                tdsr_act = (total_debt_stress / income) * 100.0
                msr_act = (bank_pmt / income) * 100.0
            else:
                tdsr_act = 0.0
                msr_act = 0.0

            rec.tdsr_actual_pct = round(tdsr_act, 2)
            rec.msr_actual_pct = round(msr_act, 2)
            rec.tdsr_passed = bool(tdsr_act <= (rec.tdsr_limit_pct or 55.0))
            rec.msr_passed = bool(msr_act <= (rec.msr_limit_pct or 30.0))
