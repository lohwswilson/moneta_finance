# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MonetaPortfolioRebalanceWizard(models.TransientModel):
    _name = 'moneta.portfolio.rebalance.wizard'
    _description = 'Portfolio Asset Allocation Rebalancer Wizard'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    total_portfolio_value = fields.Monetary(string='Total Portfolio Value', compute='_compute_rebalance_plan')
    line_ids = fields.One2many('moneta.portfolio.rebalance.line.wizard', 'wizard_id',
                               string='Rebalance Recommendations', compute='_compute_rebalance_plan')

    @api.depends('user_id')
    def _compute_rebalance_plan(self):
        for wiz in self:
            allocs = self.env['moneta.target.allocation'].search([('user_id', '=', wiz.user_id.id)])
            lines = []
            tot_val = 0.0

            for a in allocs:
                tot_val += float(a.actual_value or 0.0)
                amt = float(a.rebalance_amount or 0.0)
                act = 'buy' if amt > 0 else ('sell' if amt < 0 else 'hold')
                lines.append((0, 0, {
                    'asset_class': a.asset_class,
                    'target_weight': a.target_weight,
                    'actual_weight': a.actual_weight,
                    'drift_percent': a.drift_percent,
                    'action': act,
                    'rebalance_amount': abs(amt),
                    'notes': f"Target {a.target_weight}% vs Actual {a.actual_weight}% (Drift: {a.drift_percent:+0.1f}%)"
                }))

            wiz.total_portfolio_value = round(tot_val, 4)
            wiz.line_ids = lines


class MonetaPortfolioRebalanceLineWizard(models.TransientModel):
    _name = 'moneta.portfolio.rebalance.line.wizard'
    _description = 'Portfolio Rebalance Recommendation Line'

    wizard_id = fields.Many2one('moneta.portfolio.rebalance.wizard', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    asset_class = fields.Selection([
        ('stock', 'Stock / Equity'),
        ('etf', 'ETF'),
        ('mutual_fund', 'Mutual Fund'),
        ('bond', 'Bond / Fixed Income'),
        ('crypto', 'Cryptocurrency'),
        ('cash', 'Cash Equivalent'),
        ('real_estate', 'Real Estate / REIT'),
        ('commodities', 'Commodities / Gold'),
    ], string='Asset Class', required=True)
    target_weight = fields.Float(string='Target %')
    actual_weight = fields.Float(string='Actual %')
    drift_percent = fields.Float(string='Drift %')
    action = fields.Selection([('buy', 'BUY'), ('sell', 'SELL'), ('hold', 'BALANCED')], string='Action', required=True)
    rebalance_amount = fields.Monetary(string='Rebalance Amount')
    notes = fields.Char(string='Guidance')
