# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaPrsTracker(models.Model):
    _name = 'moneta.prs.tracker'
    _description = 'Malaysia Private Retirement Scheme (PRS) Portfolio'
    _order = 'name asc'

    name = fields.Char(string='PRS Fund Name', required=True)
    user_id = fields.Many2one('res.users', string='Investor', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.MYR', raise_if_not_found=False) or self.env.company.currency_id, required=True)

    provider = fields.Selection([
        ('principal', 'Principal Asset Management (Principal PRS)'),
        ('public_mutual', 'Public Mutual Berhad (Public Mutual PRS)'),
        ('manulife', 'Manulife Investment Management (Manulife PRS)'),
        ('affin_hwang', 'AHAM Capital / Affin Hwang PRS'),
        ('kenanga', 'Kenanga Investors Berhad (Kenanga OnePRS)'),
        ('rhb', 'RHB Asset Management (RHB PRS)'),
        ('other', 'Other PPA Approved Provider'),
    ], string='PRS Provider', default='principal', required=True)

    ppa_account_number = fields.Char(string='PPA Account #')
    current_fund_value = fields.Monetary(string='Current Fund NAV Value', required=True, default=0.0)
    total_contributions_ytd = fields.Monetary(string='Contributions YTD (Current Calendar Year)', default=0.0)
    
    prs_tax_relief_utilized = fields.Monetary(
        string='LHDN Tax Relief Claimable (Max RM3,000)',
        compute='_compute_tax_relief',
        store=True,
    )
    
    annual_return_rate_pct = fields.Float(string='Trailing 1-Yr Return (%)', digits=(5, 2), default=0.0)
    notes = fields.Text(string='Fund Allocation & Notes')

    @api.depends('total_contributions_ytd')
    def _compute_tax_relief(self):
        for rec in self:
            contrib = float(rec.total_contributions_ytd or 0.0)
            rec.prs_tax_relief_utilized = min(contrib, 3000.0)


class MonetaAsnbTracker(models.Model):
    _name = 'moneta.asnb.tracker'
    _description = 'Amanah Saham Nasional Berhad (ASNB) Unit Trust Hub'
    _order = 'fund_code asc, name asc'

    name = fields.Char(string='ASNB Fund Name', required=True)
    user_id = fields.Many2one('res.users', string='Unit Holder', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.MYR', raise_if_not_found=False) or self.env.company.currency_id, required=True)

    fund_code = fields.Selection([
        ('asb', 'Amanah Saham Bumiputera (ASB)'),
        ('asb2', 'Amanah Saham Bumiputera 2 (ASB 2)'),
        ('asb3', 'Amanah Saham Bumiputera 3 - Didik (ASB 3 Didik)'),
        ('asm', 'Amanah Saham Malaysia (ASM)'),
        ('asm2', 'Amanah Saham Malaysia 2 - Wawasan (ASM 2 Wawasan)'),
        ('asm3', 'Amanah Saham Malaysia 3 (ASM 3)'),
        ('asn', 'Amanah Saham Nasional (ASN)'),
        ('asn_equity', 'ASN Equity Series (Variable NAV)'),
        ('other', 'Other ASNB Unit Trust'),
    ], string='ASNB Fund Code', default='asm', required=True)

    fund_type = fields.Selection([
        ('fixed_price', 'Fixed Price (RM1.00 / Unit - Capital Protected)'),
        ('variable_price', 'Variable Price (Daily Floating NAV)'),
    ], string='Fund Pricing Type', default='fixed_price', required=True)

    units_held = fields.Float(string='Units Held', required=True, digits=(12, 4), default=0.0)
    unit_price = fields.Monetary(string='Price / Unit', default=1.00, required=True)
    total_market_value = fields.Monetary(string='Total Fund Value', compute='_compute_asnb_totals', store=True)

    latest_dividend_rate_pct = fields.Float(string='Latest Annual Distribution (sen / unit or %)', default=5.25, digits=(4, 2))
    annual_dividend_income = fields.Monetary(string='Estimated Annual Dividend Income', compute='_compute_asnb_totals', store=True)
    
    is_asb_financing = fields.Boolean(string='Financed via ASB Loan / ASBF', default=False)
    asbf_monthly_installment = fields.Monetary(string='Monthly ASBF Installment', default=0.0)

    notes = fields.Text(string='Notes / Target Allocation')

    @api.onchange('fund_type')
    def _onchange_fund_type(self):
        if self.fund_type == 'fixed_price':
            self.unit_price = 1.00

    @api.depends('units_held', 'unit_price', 'latest_dividend_rate_pct', 'fund_type')
    def _compute_asnb_totals(self):
        for rec in self:
            units = float(rec.units_held or 0.0)
            p = float(rec.unit_price or 1.00)
            val = units * p
            rec.total_market_value = round(val, 2)
            
            div_rate = float(rec.latest_dividend_rate_pct or 0.0) / 100.0
            rec.annual_dividend_income = round(val * div_rate, 2)
