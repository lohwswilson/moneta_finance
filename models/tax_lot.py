# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class MonetaSecurityLot(models.Model):
    _name = 'moneta.security.lot'
    _description = 'Investment Tax-Lot (Purchase Lot Tracking)'
    _order = 'purchase_date asc, id asc'

    name = fields.Char(string='Lot Identifier', compute='_compute_name', store=True)
    security_id = fields.Many2one('moneta.security', string='Security', required=True, index=True)
    account_id = fields.Many2one('moneta.account', string='Brokerage Account', required=True, index=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', related='account_id.currency_id', store=True, readonly=True)

    purchase_date = fields.Date(string='Acquisition Date', required=True, default=fields.Date.context_today)
    initial_quantity = fields.Float(string='Original Shares Bought', required=True, digits=(12, 4), default=0.0)
    remaining_quantity = fields.Float(string='Remaining Shares Held', required=True, digits=(12, 4), default=0.0)
    
    purchase_price = fields.Monetary(string='Purchase Price / Share', required=True, default=0.0)
    commission_paid = fields.Monetary(string='Commission Allocated', default=0.0)
    
    total_cost_basis = fields.Monetary(string='Total Cost Basis ($)', compute='_compute_lot_metrics', store=True)
    current_price = fields.Monetary(string='Current Price', related='security_id.current_price', readonly=True)
    current_market_value = fields.Monetary(string='Current Market Value ($)', compute='_compute_lot_metrics', store=True)
    
    unrealized_gain = fields.Monetary(string='Unrealized Gain / Loss ($)', compute='_compute_lot_metrics', store=True)
    unrealized_gain_percent = fields.Float(string='Unrealized Gain (%)', compute='_compute_lot_metrics', store=True, digits=(5, 2))
    
    holding_days = fields.Integer(string='Holding Period (Days)', compute='_compute_holding_days')
    term_type = fields.Selection([
        ('short_term', 'Short-Term (< 1 Year)'),
        ('long_term', 'Long-Term (≥ 1 Year)'),
    ], string='Holding Classification', compute='_compute_lot_metrics', store=True)

    state = fields.Selection([
        ('open', 'Open / Active Lot'),
        ('closed', 'Fully Disposed (Sold)'),
    ], string='Lot Status', compute='_compute_lot_metrics', store=True)

    purchase_transaction_id = fields.Many2one(
        'moneta.investment.transaction', string='Acquisition Trade', ondelete='cascade'
    )
    disposal_ids = fields.One2many(
        'moneta.security.lot.disposal', 'lot_id', string='Disposal History'
    )

    @api.depends('security_id.symbol', 'remaining_quantity', 'purchase_price', 'purchase_date')
    def _compute_name(self):
        for lot in self:
            sym = lot.security_id.symbol or 'SEC'
            qty = lot.remaining_quantity or lot.initial_quantity or 0.0
            price = lot.purchase_price or 0.0
            dt = lot.purchase_date or fields.Date.today()
            lot.name = f"{sym} - {qty:,.2f} shs @ ${price:,.2f} ({dt})"

    def _compute_holding_days(self):
        today = fields.Date.today()
        for lot in self:
            if lot.purchase_date:
                lot.holding_days = max((today - lot.purchase_date).days, 0)
            else:
                lot.holding_days = 0

    @api.depends('remaining_quantity', 'purchase_price', 'purchase_date', 'security_id.current_price', 'initial_quantity')
    def _compute_lot_metrics(self):
        today = fields.Date.today()
        for lot in self:
            rem = lot.remaining_quantity or 0.0
            price = lot.purchase_price or 0.0
            mkt_price = float(lot.security_id.current_price or 0.0)

            cost = rem * price
            mkt_val = rem * mkt_price
            gain = mkt_val - cost
            gain_pct = ((gain / cost) * 100.0) if cost > 0 else 0.0

            lot.total_cost_basis = round(cost, 2)
            lot.current_market_value = round(mkt_val, 2)
            lot.unrealized_gain = round(gain, 2)
            lot.unrealized_gain_percent = round(gain_pct, 2)

            days = (today - lot.purchase_date).days if lot.purchase_date else 0
            lot.term_type = 'long_term' if days >= 365 else 'short_term'
            lot.state = 'open' if rem > 1e-6 else 'closed'


class MonetaSecurityLotDisposal(models.Model):
    _name = 'moneta.security.lot.disposal'
    _description = 'Lot Disposal Allocation (Sell Trade Allocation)'
    _order = 'disposal_date desc, id desc'

    lot_id = fields.Many2one('moneta.security.lot', string='Tax Lot', required=True, ondelete='cascade')
    sell_transaction_id = fields.Many2one(
        'moneta.investment.transaction', string='Sell Trade', required=True, ondelete='cascade'
    )
    disposal_date = fields.Date(string='Disposal Date', required=True)
    currency_id = fields.Many2one('res.currency', related='lot_id.currency_id')

    quantity_sold = fields.Float(string='Shares Disposed', required=True, digits=(12, 4))
    cost_basis_sold = fields.Monetary(string='Cost Basis of Shares Sold', required=True)
    proceeds = fields.Monetary(string='Gross Proceeds', required=True)
    realized_gain = fields.Monetary(string='Realized Capital Gain / Loss', compute='_compute_realized', store=True)
    
    term_type = fields.Selection([
        ('short_term', 'Short-Term (< 1 Year)'),
        ('long_term', 'Long-Term (≥ 1 Year)'),
    ], string='Capital Gain Term', required=True)

    @api.depends('proceeds', 'cost_basis_sold')
    def _compute_realized(self):
        for rec in self:
            rec.realized_gain = round((rec.proceeds or 0.0) - (rec.cost_basis_sold or 0.0), 2)
