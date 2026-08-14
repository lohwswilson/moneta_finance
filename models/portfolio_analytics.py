# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MonetaTargetAllocation(models.Model):
    _name = 'moneta.target.allocation'
    _description = 'Target Asset Allocation & Rebalancing Matrix'
    _order = 'asset_class asc'

    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)

    asset_class = fields.Selection([
        ('stock', 'Stock / Equity'),
        ('etf', 'ETF'),
        ('mutual_fund', 'Mutual Fund'),
        ('bond', 'Bond / Fixed Income'),
        ('crypto', 'Cryptocurrency'),
        ('cash', 'Cash Equivalent'),
        ('real_estate', 'Real Estate / REIT'),
        ('commodities', 'Commodities / Gold'),
    ], string='Asset Class', required=True, default='stock')

    target_weight = fields.Float(string='Target Weight (%)', required=True, default=20.0, digits=(5, 2))
    actual_value = fields.Monetary(string='Current Value', compute='_compute_actual_allocation')
    actual_weight = fields.Float(string='Actual Weight (%)', compute='_compute_actual_allocation', digits=(5, 2))
    drift_percent = fields.Float(string='Drift (%)', compute='_compute_actual_allocation', digits=(5, 2))
    rebalance_amount = fields.Monetary(string='Required Rebalance ($)', compute='_compute_actual_allocation')

    _sql_constraints = [
        ('user_asset_uniq', 'unique(user_id, asset_class)', 'Target allocation already configured for this asset class!'),
    ]

    @api.depends('target_weight')
    def _compute_actual_allocation(self):
        user = self.env.user
        holdings = self.env['moneta.holding'].search([('user_id', '=', user.id)])
        total_mkt = sum(float(h.market_value or 0.0) for h in holdings)

        # Include liquid cash
        cash_accs = self.env['moneta.account'].search([
            ('user_id', '=', user.id),
            ('account_type', 'in', ('checking', 'chequing', 'savings', 'cash')),
            ('is_closed', '=', False),
        ])
        cash_total = sum(max(float(a.current_balance or 0.0), 0.0) for a in cash_accs)
        grand_total = total_mkt + cash_total

        # Group by asset class
        class_totals = {'cash': cash_total}
        for h in holdings:
            ac = h.asset_class or 'stock'
            class_totals[ac] = class_totals.get(ac, 0.0) + float(h.market_value or 0.0)

        for rec in self:
            val = class_totals.get(rec.asset_class, 0.0)
            rec.actual_value = round(val, 4)
            if grand_total > 0:
                act_wt = (val / grand_total) * 100.0
                rec.actual_weight = round(act_wt, 2)
                rec.drift_percent = round(act_wt - rec.target_weight, 2)
                ideal_val = (rec.target_weight / 100.0) * grand_total
                rec.rebalance_amount = round(ideal_val - val, 4)
            else:
                rec.actual_weight = 0.0
                rec.drift_percent = 0.0
                rec.rebalance_amount = 0.0


class MonetaBenchmarkComparison(models.Model):
    _name = 'moneta.benchmark.comparison'
    _description = 'Portfolio vs Benchmark Comparison (S&P 500 / VOO / VT)'
    _order = 'period asc'

    name = fields.Char(string='Comparison Name', default='S&P 500 Benchmark Comparison')
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True)
    benchmark_security_id = fields.Many2one(
        'moneta.security', string='Benchmark Index',
        domain="[('is_benchmark', '=', True)]",
    )

    period = fields.Selection([
        ('1m', '1 Month'),
        ('3m', '3 Months'),
        ('ytd', 'Year-to-Date'),
        ('1y', '1 Year'),
        ('3y', '3 Years'),
        ('5y', '5 Years'),
        ('all', 'All Time'),
    ], string='Timeframe', default='1y', required=True)

    portfolio_return_pct = fields.Float(string='Portfolio Return (%)', compute='_compute_returns', digits=(5, 2))
    benchmark_return_pct = fields.Float(string='Benchmark Return (%)', compute='_compute_returns', digits=(5, 2))
    alpha_pct = fields.Float(string='Alpha Excess Return (%)', compute='_compute_returns', digits=(5, 2))

    @api.depends('period', 'benchmark_security_id')
    def _compute_returns(self):
        today = date.today()
        for rec in self:
            days = 365
            if rec.period == '1m':
                days = 30
            elif rec.period == '3m':
                days = 90
            elif rec.period == 'ytd':
                days = (today - today.replace(month=1, day=1)).days or 1
            elif rec.period == '1y':
                days = 365
            elif rec.period == '3y':
                days = 365 * 3
            elif rec.period == '5y':
                days = 365 * 5
            elif rec.period == 'all':
                days = 365 * 10

            # Calculate user portfolio return across holdings
            holdings = self.env['moneta.holding'].search([('user_id', '=', rec.user_id.id)])
            tot_val = sum(float(h.market_value or 0.0) for h in holdings)
            tot_cost = sum(float(h.cost_basis or 0.0) for h in holdings)
            port_ret = ((tot_val - tot_cost) / tot_cost * 100.0) if tot_cost > 0 else 0.0

            # Calculate benchmark price return over timeframe
            bench_ret = 12.4  # S&P 500 historical nominal average baseline
            if rec.benchmark_security_id:
                start_date = today - timedelta(days=days)
                p_start = self.env['moneta.security.price'].search([
                    ('security_id', '=', rec.benchmark_security_id.id),
                    ('price_date', '<=', start_date),
                ], order='price_date desc', limit=1)
                p_end = self.env['moneta.security.price'].search([
                    ('security_id', '=', rec.benchmark_security_id.id),
                ], order='price_date desc', limit=1)
                if p_start and p_end and p_start.price_close > 0:
                    bench_ret = ((p_end.price_close - p_start.price_close) / p_start.price_close) * 100.0

            rec.portfolio_return_pct = round(port_ret, 2)
            rec.benchmark_return_pct = round(bench_ret, 2)
            rec.alpha_pct = round(port_ret - bench_ret, 2)
