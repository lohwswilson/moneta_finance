# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestBalanceModel(MonetaTestBase):

    def test_opening_balance_seeds_current_and_cleared(self):
        acc = self._make_account(opening_balance=1000.0)
        self.assertEqual(self._current_balance(acc), 1000.0)
        self.assertEqual(self._cleared_balance(acc), 1000.0)

    def test_transaction_delta_applies_to_balance(self):
        acc = self._make_account(opening_balance=500.0)
        self._make_transaction(acc, -100.0, state='cleared')
        self.assertEqual(self._current_balance(acc), 400.0)
        self.assertEqual(self._cleared_balance(acc), 400.0)

    def test_unreconciled_counts_in_current_not_cleared(self):
        acc = self._make_account(opening_balance=0.0)
        self._make_transaction(acc, -100.0, state='unreconciled')
        self.assertEqual(self._current_balance(acc), -100.0)
        self.assertEqual(self._cleared_balance(acc), 0.0)

    def test_void_excludes_from_balance(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -50.0, state='cleared')
        self.assertEqual(self._current_balance(acc), -50.0)
        tx.write({'state': 'void'})
        self.assertEqual(self._current_balance(acc), 0.0)
        # void -> cleared restores the contribution
        tx.write({'state': 'cleared'})
        self.assertEqual(self._current_balance(acc), -50.0)

    def test_future_dated_excluded_until_today(self):
        acc = self._make_account(opening_balance=0.0)
        future = fields.Date.context_today(self.env.user) + timedelta(days=5)
        self._make_transaction(acc, -200.0, state='cleared', transaction_date=future)
        # Not yet due -> excluded from current balance.
        self.assertEqual(self._current_balance(acc), 0.0)

    def test_unlink_reverses_balance(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -75.0, state='cleared')
        self.assertEqual(self._current_balance(acc), -75.0)
        tx.unlink()
        self.assertEqual(self._current_balance(acc), 0.0)

    def test_recompute_after_opening_balance_change(self):
        acc = self._make_account(opening_balance=100.0)
        self._make_transaction(acc, -30.0, state='cleared')
        self.assertEqual(self._current_balance(acc), 70.0)
        # Change the opening balance -> recompute.
        acc.write({'opening_balance': 500.0})
        self.assertEqual(self._current_balance(acc), 470.0)

    def test_amount_change_applies_delta(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -100.0, state='cleared')
        self.assertEqual(self._current_balance(acc), -100.0)
        tx.write({'amount': -250.0})
        self.assertEqual(self._current_balance(acc), -250.0)

    def test_move_transaction_between_accounts(self):
        acc1 = self._make_account(name='Src', opening_balance=0.0)
        acc2 = self._make_account(name='Dst', opening_balance=0.0)
        tx = self._make_transaction(acc1, -100.0, state='cleared')
        self.assertEqual(self._current_balance(acc1), -100.0)
        tx.write({'account_id': acc2.id})
        self.assertEqual(self._current_balance(acc1), 0.0)
        self.assertEqual(self._current_balance(acc2), -100.0)