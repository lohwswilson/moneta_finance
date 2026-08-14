# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta
from odoo import models, fields, api


class MonetaDashboard(models.TransientModel):
    _name = 'moneta.dashboard'
    _description = 'Moneta Dashboard Snapshot'

    # All computes run in the opener's env, so record rules scope every search
    # to the current user -- the tiles are per-owner by construction.
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, required=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    net_worth = fields.Monetary(string='Net Worth', compute='_compute_totals')
    month_income = fields.Monetary(string='This Month Income', compute='_compute_totals')
    month_expenses = fields.Monetary(string='This Month Expenses', compute='_compute_totals')
    upcoming_bill_count = fields.Integer(string='Upcoming Bills (14 days)', compute='_compute_upcoming_bills')
    upcoming_bills_total = fields.Monetary(string='Upcoming Bills Total', compute='_compute_upcoming_bills')

    @api.depends()
    def _compute_totals(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        for dash in self:
            # Net worth: the current month's monthly-snapshot aggregation
            # (assets abs - liabilities abs, converted to the base currency at
            # the month's rate, exclude_from_net_worth honored). Snapshots are
            # maintained rebuild-on-write + a daily cron.
            dash.net_worth = self.env['moneta.account.balance.monthly']._net_worth_for_month(
                month_start
            )
            # Month income/expense from non-void transactions (parent amounts
            # only; split children live in a separate model and are never
            # double-counted).
            txs = self.env['moneta.transaction'].search([
                ('transaction_date', '>=', month_start),
                ('transaction_date', '<=', month_end),
                ('state', '!=', 'void'),
            ])
            income = 0.0
            expenses = 0.0
            for tx in txs:
                if tx.amount > 0:
                    income += float(tx.amount or 0.0)
                else:
                    expenses += float(tx.amount or 0.0)
            dash.month_income = round(income, 4)
            dash.month_expenses = round(-expenses, 4)

    @api.depends()
    def _compute_upcoming_bills(self):
        """Bills due within the next 14 days from recurring schedules."""
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=14)
        for dash in self:
            scheds = self.env['moneta.recurring.transaction'].search([
                ('active', '=', True),
                ('next_date', '>=', today),
                ('next_date', '<=', horizon),
                ('amount', '<', 0),
            ])
            dash.upcoming_bill_count = len(scheds)
            dash.upcoming_bills_total = round(
                -sum(float(s.amount or 0.0) for s in scheds), 4
            )

    def action_recompute(self):
        """Refresh the tiles (clears the compute cache so the next read
        recomputes)."""
        self.invalidate_recordset()
        return True