# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api


class MonetaSubscriptionDetector(models.TransientModel):
    _name = 'moneta.subscription.detector'
    _description = 'Moneta Smart Subscription & Recurring Outflow Detector'

    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    lookback_days = fields.Integer(string='Lookback Period (Days)', default=180, required=True)
    line_ids = fields.One2many('moneta.subscription.detector.line', 'detector_id', string='Detected Subscriptions')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        start_date = today - timedelta(days=180)

        txs = self.env['moneta.transaction'].search([
            ('transaction_date', '>=', start_date),
            ('amount', '<', 0),
            ('state', '!=', 'void'),
            ('is_transfer', '=', False),
        ], order='transaction_date asc')

        # Group by Payee
        payee_txs = {}
        for tx in txs:
            if not tx.payee_id:
                continue
            payee_txs.setdefault(tx.payee_id, []).append(tx)

        lines = []
        for payee, p_txs in payee_txs.items():
            if len(p_txs) < 2:
                continue

            # Calculate average interval between consecutive charges
            dates = [t.transaction_date for t in p_txs]
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            avg_interval = sum(intervals) / len(intervals)

            # Determine frequency
            freq = None
            if 20 <= avg_interval <= 40:
                freq = 'monthly'
            elif 6 <= avg_interval <= 10:
                freq = 'weekly'
            elif 12 <= avg_interval <= 18:
                freq = 'biweekly'
            elif 80 <= avg_interval <= 100:
                freq = 'quarterly'
            elif 340 <= avg_interval <= 390:
                freq = 'yearly'

            if freq:
                amounts = [abs(float(t.amount or 0.0)) for t in p_txs]
                avg_amt = sum(amounts) / len(amounts)
                last_tx = p_txs[-1]

                lines.append((0, 0, {
                    'payee_id': payee.id,
                    'frequency': freq,
                    'average_amount': round(avg_amt, 4),
                    'last_charge_date': last_tx.transaction_date,
                    'charge_count': len(p_txs),
                    'category_id': last_tx.category_id.id if last_tx.category_id else False,
                    'account_id': last_tx.account_id.id if last_tx.account_id else False,
                    'currency_id': last_tx.currency_id.id if last_tx.currency_id else False,
                }))

        res['line_ids'] = lines
        return res


class MonetaSubscriptionDetectorLine(models.TransientModel):
    _name = 'moneta.subscription.detector.line'
    _description = 'Detected Subscription Line'
    _order = 'average_amount desc'

    detector_id = fields.Many2one('moneta.subscription.detector', string='Detector', ondelete='cascade')
    payee_id = fields.Many2one('moneta.payee', string='Payee / Service', required=True)
    category_id = fields.Many2one('moneta.category', string='Category')
    account_id = fields.Many2one('moneta.account', string='Account')
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Biweekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Detected Cadence', required=True)
    average_amount = fields.Monetary(string='Avg Charge ($)', required=True)
    last_charge_date = fields.Date(string='Last Billed')
    charge_count = fields.Integer(string='Times Charged')
    currency_id = fields.Many2one('res.currency', string='Currency')

    def action_create_recurring_bill(self):
        """1-click convert detected subscription into a tracked Recurring Bill."""
        self.ensure_one()
        # Compute next expected due date
        next_dt = self.last_charge_date or fields.Date.context_today(self)
        if self.frequency == 'monthly':
            next_dt = next_dt + timedelta(days=30)
        elif self.frequency == 'yearly':
            next_dt = next_dt + timedelta(days=365)
        elif self.frequency == 'weekly':
            next_dt = next_dt + timedelta(days=7)
        elif self.frequency == 'biweekly':
            next_dt = next_dt + timedelta(days=14)

        bill = self.env['moneta.recurring.transaction'].create({
            'name': f"{self.payee_id.name} Subscription",
            'payee_id': self.payee_id.id,
            'account_id': self.account_id.id if self.account_id else self.env['moneta.account'].search([], limit=1).id,
            'category_id': self.category_id.id if self.category_id else False,
            'amount': -abs(self.average_amount),
            'frequency': self.frequency,
            'next_date': next_dt,
            'auto_post': True,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Subscription Tracked',
                'message': f"Created recurring bill schedule for '{bill.name}'.",
                'type': 'success',
                'sticky': False,
            }
        }
