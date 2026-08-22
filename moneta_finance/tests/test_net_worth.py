# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestNetWorth(MonetaTestBase):

    def _rows(self, account):
        return self.env['moneta.account.balance.monthly'].search(
            [('account_id', '=', account.id)], order='month'
        )

    def test_transaction_creates_monthly_rows(self):
        acc = self._make_account(opening_balance=1000.0)
        today = fields.Date.context_today(self.env.user)
        self._make_transaction(acc, -200.0, transaction_date=today)
        rows = self._rows(acc)
        self.assertTrue(rows)
        current = rows.filtered(lambda r: r.month == today.replace(day=1))
        self.assertTrue(current)
        # End-of-month balance = opening + the transaction.
        self.assertEqual(round(current.balance, 4), 800.0)

    def test_rebuild_on_edit(self):
        acc = self._make_account(opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        tx = self._make_transaction(acc, -100.0, transaction_date=today)
        current = self._rows(acc).filtered(lambda r: r.month == today.replace(day=1))
        self.assertEqual(round(current.balance, 4), -100.0)
        tx.write({'amount': -300.0})
        current.invalidate_recordset(['balance'])
        self.assertEqual(round(current.balance, 4), -300.0)

    def test_void_transaction_excluded_from_monthly(self):
        acc = self._make_account(opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        tx = self._make_transaction(acc, -50.0, transaction_date=today)
        current = self._rows(acc).filtered(lambda r: r.month == today.replace(day=1))
        self.assertEqual(round(current.balance, 4), -50.0)
        tx.write({'state': 'void'})
        current.invalidate_recordset(['balance'])
        self.assertEqual(round(current.balance, 4), 0.0)

    def test_market_value_snapshot(self):
        acc = self._make_account(name='Brokerage', account_type='brokerage', opening_balance=0.0)
        sec = self.env['moneta.security'].create({'name': 'Test Inc', 'symbol': 'TST'})
        self.env['moneta.security.price'].create({
            'security_id': sec.id, 'price_date': '2026-07-01', 'price_close': 50.0,
        })
        self.env['moneta.investment.transaction'].create({
            'action': 'buy',
            'account_id': acc.id,
            'security_id': sec.id,
            'trade_date': '2026-07-10',
            'quantity': 10.0,
            'price': 40.0,
        })
        rows = self._rows(acc)
        july = rows.filtered(lambda r: r.month == fields.Date.to_date('2026-07-01'))
        self.assertTrue(july)
        # July market value: 10 shares x 50 (price as of July 31).
        self.assertEqual(round(july.market_value or 0.0, 4), 500.0)

    def test_net_worth_aggregation(self):
        # Use a dedicated (non-admin) user so the account.balance.monthly record
        # rule scopes _net_worth_for_month to only these accounts; admin bypasses
        # record rules and would sum the live DB's real accounts too.
        user = self._make_user('Net Worth User', 'net_worth_user')
        Acc = self.env['moneta.account'].with_user(user)
        Acc.create({'name': 'Checking', 'account_type': 'checking', 'opening_balance': 1000.0, 'currency_id': self.currency.id})
        Acc.create({'name': 'Visa', 'account_type': 'credit_card', 'opening_balance': -500.0, 'currency_id': self.currency.id})
        Acc.create({'name': 'Loan', 'account_type': 'loan', 'opening_balance': -2500.0, 'currency_id': self.currency.id})
        today = fields.Date.context_today(self.env.user)
        net = self.env['moneta.account.balance.monthly'].with_user(user)._net_worth_for_month(today.replace(day=1))
        self.assertEqual(net, -2000.0)

    def test_exclude_from_net_worth(self):
        user = self._make_user('Net Worth User 2', 'net_worth_user2')
        Acc = self.env['moneta.account'].with_user(user)
        Acc.create({'name': 'Checking', 'account_type': 'checking', 'opening_balance': 1000.0, 'currency_id': self.currency.id})
        hidden = Acc.create({'name': 'Hidden', 'account_type': 'asset', 'opening_balance': 9999.0, 'currency_id': self.currency.id})
        hidden.write({'exclude_from_net_worth': True})
        today = fields.Date.context_today(self.env.user)
        net = self.env['moneta.account.balance.monthly'].with_user(user)._net_worth_for_month(today.replace(day=1))
        self.assertEqual(net, 1000.0)

    def test_cron_rolls_monthly_balances(self):
        acc = self._make_account(opening_balance=500.0)
        self.env['moneta.account.balance.monthly']._cron_roll_monthly_balances()
        today = fields.Date.context_today(self.env.user)
        rows = self._rows(acc)
        self.assertTrue(rows.filtered(lambda r: r.month == today.replace(day=1)))