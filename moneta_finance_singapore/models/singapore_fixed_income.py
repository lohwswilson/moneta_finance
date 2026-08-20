# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class MonetaSSBBond(models.Model):
    _name = 'moneta.ssb.bond'
    _description = 'Singapore Savings Bonds (SSB) 10-Year Step-Up Bond Engine'
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Bond Name', compute='_compute_name', store=True)
    issue_code = fields.Char(string='SSB Issue Code', required=True, default='SBJAN26 GX26010T', help='e.g. SBJAN26 GX26010T')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    issue_date = fields.Date(string='Issue Date', required=True, default=fields.Date.context_today)
    maturity_date = fields.Date(string='Maturity Date (10 Years)', compute='_compute_dates', store=True)
    
    investment_amount = fields.Monetary(string='Principal Invested (Max $200k)', required=True, default=10000.0)
    funding_source = fields.Selection([
        ('cash', 'Cash (Bank Account)'),
        ('srs', 'Supplementary Retirement Scheme (SRS)'),
    ], string='Funding Source', default='cash', required=True)

    linked_account_id = fields.Many2one('moneta.account', string='Linked Bank / SRS Account')

    # 10-Year Step-Up Coupon Rates (% p.a.)
    rate_year_1 = fields.Float(string='Year 1 Rate (%)', default=2.80, digits=(5, 2))
    rate_year_2 = fields.Float(string='Year 2 Rate (%)', default=2.85, digits=(5, 2))
    rate_year_3 = fields.Float(string='Year 3 Rate (%)', default=2.90, digits=(5, 2))
    rate_year_4 = fields.Float(string='Year 4 Rate (%)', default=2.95, digits=(5, 2))
    rate_year_5 = fields.Float(string='Year 5 Rate (%)', default=3.00, digits=(5, 2))
    rate_year_6 = fields.Float(string='Year 6 Rate (%)', default=3.05, digits=(5, 2))
    rate_year_7 = fields.Float(string='Year 7 Rate (%)', default=3.10, digits=(5, 2))
    rate_year_8 = fields.Float(string='Year 8 Rate (%)', default=3.15, digits=(5, 2))
    rate_year_9 = fields.Float(string='Year 9 Rate (%)', default=3.20, digits=(5, 2))
    rate_year_10 = fields.Float(string='Year 10 Rate (%)', default=3.30, digits=(5, 2))

    average_10yr_yield = fields.Float(string='10-Year Average Yield (%)', compute='_compute_yields', store=True, digits=(5, 2))
    total_interest_to_maturity = fields.Monetary(string='Total Interest Over 10 Years', compute='_compute_yields', store=True)
    next_coupon_payout = fields.Monetary(string='Next Semi-Annual Coupon ($)', compute='_compute_yields', store=True)

    state = fields.Selection([
        ('active', 'Active (Held)'),
        ('redeemed', 'Redeemed Early'),
        ('matured', 'Matured (10 Yrs)'),
    ], string='Status', default='active', required=True)

    redemption_date = fields.Date(string='Redemption Date')
    redemption_fee = fields.Monetary(string='MAS Redemption Fee', default=2.0)
    actual_interest_received = fields.Monetary(string='Total Interest Received to Date', default=0.0)

    notes = fields.Text(string='Notes')

    @api.constrains('investment_amount')
    def _check_ssb_limit(self):
        for rec in self:
            if rec.investment_amount % 500 != 0:
                raise ValidationError("SSB investment amount must be in multiples of SGD $500.")
            if rec.investment_amount > 200000.0:
                raise ValidationError("Singapore Savings Bonds have an individual holding cap of SGD $200,000 across all issues.")

    @api.depends('issue_code', 'investment_amount')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.issue_code or 'SSB'} - ${rec.investment_amount:,.0f}"

    @api.depends('issue_date')
    def _compute_dates(self):
        for rec in self:
            if rec.issue_date:
                rec.maturity_date = rec.issue_date + relativedelta(years=10)
            else:
                rec.maturity_date = False

    @api.depends('investment_amount', 'rate_year_1', 'rate_year_2', 'rate_year_3', 'rate_year_4',
                 'rate_year_5', 'rate_year_6', 'rate_year_7', 'rate_year_8', 'rate_year_9', 'rate_year_10')
    def _compute_yields(self):
        for rec in self:
            amt = rec.investment_amount or 0.0
            rates = [
                rec.rate_year_1 or 0.0, rec.rate_year_2 or 0.0, rec.rate_year_3 or 0.0, rec.rate_year_4 or 0.0,
                rec.rate_year_5 or 0.0, rec.rate_year_6 or 0.0, rec.rate_year_7 or 0.0, rec.rate_year_8 or 0.0,
                rec.rate_year_9 or 0.0, rec.rate_year_10 or 0.0
            ]
            avg_yield = sum(rates) / 10.0
            rec.average_10yr_yield = round(avg_yield, 2)

            # Total interest = sum of annual interests
            tot_int = sum(amt * (r / 100.0) for r in rates)
            rec.total_interest_to_maturity = round(tot_int, 2)

            # Next semi-annual coupon = Year 1 rate / 2 * investment
            rec.next_coupon_payout = round(amt * ((rec.rate_year_1 or 0.0) / 100.0) / 2.0, 2)


class MonetaTBill(models.Model):
    _name = 'moneta.tbill'
    _description = 'MAS Treasury Bill (T-Bill) Discount Auction Engine'
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='T-Bill Name', compute='_compute_name', store=True)
    issue_code = fields.Char(string='T-Bill Issue Code', required=True, default='BS26105A', help='e.g. BS26105A (6-month) or BY26101X (1-year)')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    tenure_type = fields.Selection([
        ('6_month', '6-Month MAS T-Bill (~182 Days)'),
        ('1_year', '1-Year MAS T-Bill (~364 Days)'),
    ], string='Tenure', default='6_month', required=True)

    auction_date = fields.Date(string='Auction Date', default=fields.Date.context_today)
    issue_date = fields.Date(string='Issue Date', required=True, default=fields.Date.context_today)
    maturity_date = fields.Date(string='Maturity Date', compute='_compute_maturity', store=True)

    funding_source = fields.Selection([
        ('cash', 'Cash (Bank Account)'),
        ('cpf_oa', 'CPF Ordinary Account (OA - min $20k buffer)'),
        ('cpf_sa', 'CPF Special Account (SA - min $40k buffer)'),
        ('srs', 'Supplementary Retirement Scheme (SRS)'),
    ], string='Funding Source', default='cash', required=True)

    linked_account_id = fields.Many2one('moneta.account', string='Linked Funding Account')

    face_value = fields.Monetary(string='Face Value / Par ($)', required=True, default=10000.0)
    issue_price_per_hundred = fields.Float(string='Cut-Off Issue Price ($ / $100)', required=True, default=98.15, digits=(6, 4))
    
    total_investment_cost = fields.Monetary(string='Actual Investment Cost ($)', compute='_compute_tbill_economics', store=True)
    net_discount_profit = fields.Monetary(string='Discount Profit at Maturity ($)', compute='_compute_tbill_economics', store=True)
    cut_off_yield_p_a = fields.Float(string='Annualized Cut-Off Yield (%)', compute='_compute_tbill_economics', store=True, digits=(5, 2))
    
    days_to_maturity = fields.Integer(string='Days to Maturity', compute='_compute_maturity_countdown')
    state = fields.Selection([
        ('active', 'Active (Holding to Maturity)'),
        ('matured', 'Matured & Redeemed at Par'),
    ], string='Status', default='active', required=True)

    notes = fields.Text(string='Notes')

    @api.depends('issue_code', 'face_value')
    def _compute_name(self):
        for rec in self:
            rec.name = f"MAS T-Bill {rec.issue_code or ''} (${rec.face_value:,.0f})"

    @api.depends('issue_date', 'tenure_type')
    def _compute_maturity(self):
        for rec in self:
            if rec.issue_date:
                days = 182 if rec.tenure_type == '6_month' else 364
                rec.maturity_date = rec.issue_date + relativedelta(days=days)
            else:
                rec.maturity_date = False

    @api.depends('face_value', 'issue_price_per_hundred', 'tenure_type')
    def _compute_tbill_economics(self):
        for rec in self:
            face = rec.face_value or 0.0
            price_ratio = (rec.issue_price_per_hundred or 100.0) / 100.0
            cost = face * price_ratio
            profit = max(face - cost, 0.0)

            rec.total_investment_cost = round(cost, 2)
            rec.net_discount_profit = round(profit, 2)

            days = 182 if rec.tenure_type == '6_month' else 364
            if cost > 0 and days > 0:
                yield_p_a = (profit / cost) * (365.0 / days) * 100.0
                rec.cut_off_yield_p_a = round(yield_p_a, 2)
            else:
                rec.cut_off_yield_p_a = 0.0

    def _compute_maturity_countdown(self):
        today = fields.Date.today()
        for rec in self:
            if rec.maturity_date:
                diff = (rec.maturity_date - today).days
                rec.days_to_maturity = max(diff, 0)
            else:
                rec.days_to_maturity = 0


class MonetaUCITSETFComparator(models.Model):
    _name = 'moneta.ucits.etf.comparator'
    _description = 'Irish UCITS vs US-Domiciled ETF Tax Drag & Estate Tax Comparator'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Comparison Title', required=True, default='S&P 500: VOO (US) vs CSPX (Irish UCITS)')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    portfolio_value = fields.Monetary(string='Invested Portfolio Value ($)', required=True, default=200000.0)
    dividend_yield_pct = fields.Float(string='Index Dividend Yield (%)', default=1.50, digits=(5, 2))
    expected_growth_rate = fields.Float(string='Expected Annual Price Growth (%)', default=8.0, digits=(5, 2))
    investment_horizon_years = fields.Integer(string='Investment Horizon (Years)', default=20, required=True)

    # Tax Rates
    us_withholding_tax_pct = fields.Float(string='US-Domiciled Dividend WHT (%)', default=30.0)
    ucits_withholding_tax_pct = fields.Float(string='Irish UCITS Dividend WHT (%)', default=15.0)
    us_estate_tax_threshold = fields.Monetary(string='US Estate Tax Exemption Threshold', default=60000.0)

    # Computed Comparisons
    annual_dividend_gross = fields.Monetary(string='Gross Annual Dividends ($)', compute='_compute_comparison', store=True)
    us_etf_annual_tax_drag = fields.Monetary(string='VOO (US) Annual Tax Drag (30%)', compute='_compute_comparison', store=True)
    ucits_annual_tax_drag = fields.Monetary(string='CSPX (UCITS) Annual Tax Drag (15%)', compute='_compute_comparison', store=True)
    annual_tax_savings_with_ucits = fields.Monetary(string='Annual Dividend Tax Saved with UCITS', compute='_compute_comparison', store=True)

    cumulative_tax_savings_horizon = fields.Monetary(string='Projected Cumulative Tax Saved (Compounded)', compute='_compute_comparison', store=True)
    us_estate_tax_exposure = fields.Monetary(string='VOO US Estate Tax Liability Risk (~40%)', compute='_compute_comparison', store=True)
    ucits_estate_tax_exposure = fields.Monetary(string='CSPX Irish UCITS Estate Tax Liability ($0)', compute='_compute_comparison', store=True)

    notes = fields.Text(string='Analysis & Key Insights')

    @api.depends('portfolio_value', 'dividend_yield_pct', 'investment_horizon_years', 'us_withholding_tax_pct', 'ucits_withholding_tax_pct')
    def _compute_comparison(self):
        for rec in self:
            val = rec.portfolio_value or 0.0
            div_yield = (rec.dividend_yield_pct or 1.5) / 100.0
            gross_div = val * div_yield
            rec.annual_dividend_gross = round(gross_div, 2)

            us_drag = gross_div * ((rec.us_withholding_tax_pct or 30.0) / 100.0)
            ucits_drag = gross_div * ((rec.ucits_withholding_tax_pct or 15.0) / 100.0)
            diff = us_drag - ucits_drag

            rec.us_etf_annual_tax_drag = round(us_drag, 2)
            rec.ucits_annual_tax_drag = round(ucits_drag, 2)
            rec.annual_tax_savings_with_ucits = round(diff, 2)

            # Cumulative compounded savings over horizon
            horizon = rec.investment_horizon_years or 20
            growth = (rec.expected_growth_rate or 8.0) / 100.0
            cum_savings = sum(diff * ((1.0 + growth) ** y) for y in range(horizon))
            rec.cumulative_tax_savings_horizon = round(cum_savings, 2)

            # US Estate tax on holdings exceeding $60,000 (top rate ~40%)
            taxable_estate = max(val - (rec.us_estate_tax_threshold or 60000.0), 0.0)
            rec.us_estate_tax_exposure = round(taxable_estate * 0.40, 2)
            rec.ucits_estate_tax_exposure = 0.0
