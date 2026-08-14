# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api

# Account types treated as liabilities for net-worth aggregation (Moneta).
_LIABILITY_TYPES = ('credit_card', 'loan', 'mortgage', 'loc')


class MonetaAccountBalanceMonthly(models.Model):
    _name = 'moneta.account.balance.monthly'
    _description = 'Moneta Monthly Account Balance Snapshot'
    _order = 'month desc, account_id'

    account_id = fields.Many2one('moneta.account', string='Account', required=True, ondelete='cascade')
    month = fields.Date(string='Month', required=True, help='First day of the snapshot month')
    # End-of-month balance: opening balance + balance-affecting transactions
    # dated on or before the last day of the month.
    balance = fields.Monetary(string='End-of-Month Balance', default=0.0)
    # Holdings market value at month-end for brokerage accounts; NULL for
    # non-brokerage accounts and when any holding lacks a price as of the date.
    market_value = fields.Monetary(string='Market Value')

    # Contribution to net worth in the company (base) currency: assets carry
    # their balance, liabilities their absolute value negated, respecting
    # exclude_from_net_worth. Computed on read (currency conversion at the
    # month's rate).
    base_contribution = fields.Monetary(string='Base Currency Contribution', compute='_compute_base_contribution', store=True, group_operator='sum')

    currency_id = fields.Many2one('res.currency', related='account_id.currency_id', store=True, readonly=True)
    # Stored related owner so the per-user record rule resolves to the account owner.
    user_id = fields.Many2one('res.users', related='account_id.user_id', store=True, index=True)

    _sql_constraints = [
        ('account_month_uniq', 'unique(account_id, month)',
         'A balance snapshot already exists for this account and month.'),
    ]

    @api.depends('balance', 'month', 'currency_id', 'account_id.account_type',
                 'account_id.exclude_from_net_worth')
    def _compute_base_contribution(self):
        company = self.env.company
        base = company.currency_id
        for row in self:
            if row.account_id.exclude_from_net_worth:
                row.base_contribution = 0.0
                continue
            amount = row.balance or 0.0
            if row.account_id.account_type in _LIABILITY_TYPES:
                amount = -abs(amount)
            if row.currency_id.id == base.id:
                row.base_contribution = round(amount, 4)
            else:
                try:
                    # Convert at the month's rate (Odoo res.currency.rate,
                    # ~6dp vs Moneta's 10dp -- documented deviation).
                    row.base_contribution = round(
                        row.currency_id._convert(amount, base, company, row.month), 4
                    )
                except Exception:  # noqa: BLE001 - a missing rate leaves the
                    # contribution unknown; treat as 0 for the MVP.
                    row.base_contribution = 0.0

    # ------------------------------------------------------------------
    # Rebuild-on-write
    # ------------------------------------------------------------------

    @api.model
    def _market_value_as_of(self, account, as_of):
        """Holdings market value for a brokerage account at a date: quantity
        as of the date (buys/sells/splits from investment transactions) times
        the latest price on or before the date. False when any holding with a
        quantity lacks a price as of that date (null propagation); 0.0 for a
        brokerage with no holdings (known zero); False for non-brokerage."""
        if account.account_type != 'brokerage':
            return False
        holdings = self.env['moneta.holding'].search([('account_id', '=', acc_id)])
        if not holdings:
            return 0.0
        total = 0.0
        unknown = False
        Tx = self.env['moneta.investment.transaction']
        Price = self.env['moneta.security.price']
        for holding in holdings:
            qty = 0.0
            for tx in Tx.search([
                ('account_id', '=', account.id),
                ('security_id', '=', holding.security_id.id),
                ('trade_date', '<=', as_of),
            ], order='trade_date, id'):
                if tx.action == 'buy':
                    qty += tx.quantity or 0.0
                elif tx.action == 'sell':
                    qty -= tx.quantity or 0.0
                elif tx.action == 'split':
                    qty *= tx.quantity or 1.0
            if qty:
                price = Price.search([
                    ('security_id', '=', holding.security_id.id),
                    ('price_date', '<=', as_of),
                ], order='price_date desc', limit=1)
                if price:
                    total += qty * (price.price_close or 0.0)
                else:
                    unknown = True
        return False if unknown else round(total, 4)

    @api.model
    def _rebuild_for_account(self, account):
        acc_id = account._origin.id if hasattr(account, '_origin') and account._origin.id else account.id
        if not acc_id or not isinstance(acc_id, int):
            return
        """Rebuild the monthly snapshot rows for one account (rebuild-on-write,
        mirroring Moneta's monthly_account_balances). Every month from the
        account's opening-balance date (or earliest transaction) through the
        current month gets an end-of-month balance and, for brokerage accounts,
        a holdings market value as of month-end."""
        today = fields.Date.context_today(self)
        Tx = self.env['moneta.transaction']
        first_date = account.opening_balance_date or today
        earliest = Tx.search([('account_id', '=', acc_id)], order='transaction_date asc', limit=1)
        if earliest and earliest.transaction_date and earliest.transaction_date < first_date:
            first_date = earliest.transaction_date
        # Investment activity extends the range too (a brokerage may hold
        # securities without any cash transaction).
        earliest_inv = self.env['moneta.investment.transaction'].search(
            [('account_id', '=', acc_id)], order='trade_date asc', limit=1
        )
        if earliest_inv and earliest_inv.trade_date and earliest_inv.trade_date < first_date:
            first_date = earliest_inv.trade_date
        # Odoo 18 defers SQL writes to flush; the balance query must see them.
        self.env.flush_all()
        current_month = today.replace(day=1)
        month = first_date.replace(day=1)
        while month <= current_month:
            if month.month == 12:
                month_end = month.replace(month=12, day=31)
            else:
                month_end = (month.replace(month=month.month + 1, day=1) - timedelta(days=1))
            self.env.cr.execute(
                "SELECT COALESCE(SUM(amount), 0)::float FROM moneta_transaction "
                "WHERE account_id = %s AND state <> 'void' AND transaction_date <= %s",
                (acc_id, month_end),
            )
            balance = round(
                float(account.opening_balance or 0.0) + float(self.env.cr.fetchone()[0] or 0.0),
                4,
            )
            market_value = self._market_value_as_of(account, month_end)
            row = self.search([
                ('account_id', '=', account.id),
                ('month', '=', month),
            ], limit=1)
            vals = {'balance': balance, 'market_value': market_value}
            if row:
                row.write(vals)
            else:
                self.create(dict(vals, account_id=account.id, month=month))
            if month.month == 12:
                month = month.replace(year=month.year + 1, month=1)
            else:
                month = month.replace(month=month.month + 1)

    @api.model
    def _net_worth_for_month(self, month):
        """Net worth at a month: sum of the per-account base contributions
        (assets abs - liabilities abs, exclude flag honored), scoped to the
        current user by record rules."""
        rows = self.search([('month', '=', month)])
        return round(sum(float(r.base_contribution or 0.0) for r in rows), 4)

    @api.model
    def _cron_roll_monthly_balances(self):
        """Daily cron: rebuild every active account so the current month's
        snapshot exists (new-month rollover) and any drift is corrected. Runs
        under sudo; ownership flows through the stored related user_id."""
        Account = self.env['moneta.account'].sudo()
        for account in Account.search([('is_closed', '=', False)]):
            self.sudo()._rebuild_for_account(account)