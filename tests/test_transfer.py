# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestTransfer(MonetaTestBase):

    def test_transfer_creates_two_linked_legs(self):
        acc1 = self._make_account(name='Checking', opening_balance=1000.0)
        acc2 = self._make_account(name='Savings', opening_balance=500.0)
        tx = self.env['moneta.transaction'].create({
            'account_id': acc1.id,
            'amount': -200.0,
            'is_transfer': True,
            'transfer_account_id': acc2.id,
            'state': 'cleared',
        })
        # Counterpart exists in the target account with the opposite sign.
        cp = tx.linked_transaction_id
        self.assertTrue(cp)
        self.assertEqual(cp.account_id, acc2)
        self.assertEqual(round(cp.amount, 4), 200.0)
        self.assertEqual(cp.linked_transaction_id, tx)
        self.assertTrue(cp.is_transfer)
        # Both balances moved.
        self.assertEqual(self._current_balance(acc1), 800.0)
        self.assertEqual(self._current_balance(acc2), 700.0)

    def test_transfer_to_same_account_rejected(self):
        acc = self._make_account(opening_balance=100.0)
        with self.assertRaises(ValidationError):
            self.env['moneta.transaction'].create({
                'account_id': acc.id,
                'amount': -50.0,
                'is_transfer': True,
                'transfer_account_id': acc.id,
                'state': 'cleared',
            })

    def test_transfer_amount_change_propagates_to_counterpart(self):
        acc1 = self._make_account(name='Checking', opening_balance=0.0)
        acc2 = self._make_account(name='Savings', opening_balance=0.0)
        tx = self.env['moneta.transaction'].create({
            'account_id': acc1.id,
            'amount': -100.0,
            'is_transfer': True,
            'transfer_account_id': acc2.id,
            'state': 'cleared',
        })
        self.assertEqual(self._current_balance(acc1), -100.0)
        self.assertEqual(self._current_balance(acc2), 100.0)
        # Edit the source leg amount -> counterpart mirrors (negated).
        tx.write({'amount': -300.0})
        self.assertEqual(self._current_balance(acc1), -300.0)
        self.assertEqual(self._current_balance(acc2), 300.0)

    def test_unlink_transfer_removes_both_legs(self):
        acc1 = self._make_account(name='Checking', opening_balance=1000.0)
        acc2 = self._make_account(name='Savings', opening_balance=0.0)
        tx = self.env['moneta.transaction'].create({
            'account_id': acc1.id,
            'amount': -200.0,
            'is_transfer': True,
            'transfer_account_id': acc2.id,
            'state': 'cleared',
        })
        cp = tx.linked_transaction_id
        tx.unlink()
        self.assertFalse(cp.exists())
        # Both balances reverted.
        self.assertEqual(self._current_balance(acc1), 1000.0)
        self.assertEqual(self._current_balance(acc2), 0.0)