# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestTransfer(MonetaTestBase):

    def test_transfer_creates_two_linked_legs(self):
        acc1 = self._make_account(name='Checking', opening_balance=1000.0)
        acc2 = self._make_account(name='Savings', opening_balance=500.0)
        acc1._sync_transfer_category()
        acc2._sync_transfer_category()
        
        cat2 = self.env['moneta.category'].search([('transfer_account_id', '=', acc2.id)], limit=1)
        
        tx = self.env['moneta.transaction'].create({
            'account_id': acc1.id,
            'amount': -200.0,
            'category_id': cat2.id,
            'state': 'cleared',
        })
        # Counterpart exists in the target account with the opposite sign.
        cp = tx.linked_transaction_id
        self.assertTrue(cp)
        self.assertEqual(cp.account_id, acc2)
        self.assertEqual(round(cp.amount, 4), 200.0)
        self.assertEqual(cp.linked_transaction_id, tx)
        self.assertTrue(cp.is_transfer)
        self.assertEqual(cp.category_id.transfer_account_id, acc1)
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

    def test_transfer_move_target_account(self):
        acc1 = self._make_account(name='Checking', opening_balance=1000.0)
        acc2 = self._make_account(name='Savings', opening_balance=500.0)
        acc3 = self._make_account(name='Investment Cash', opening_balance=200.0)
        acc1._sync_transfer_category()
        acc2._sync_transfer_category()
        acc3._sync_transfer_category()
        
        cat2 = self.env['moneta.category'].search([('transfer_account_id', '=', acc2.id)], limit=1)
        cat3 = self.env['moneta.category'].search([('transfer_account_id', '=', acc3.id)], limit=1)
        
        tx = self.env['moneta.transaction'].create({
            'account_id': acc1.id,
            'amount': -200.0,
            'category_id': cat2.id,
            'state': 'cleared',
        })
        cp = tx.linked_transaction_id
        self.assertEqual(cp.account_id, acc2)
        self.assertEqual(self._current_balance(acc2), 700.0)
        self.assertEqual(self._current_balance(acc3), 200.0)
        
        # Move destination to acc3
        tx.write({'category_id': cat3.id})
        self.assertEqual(cp.account_id, acc3)
        self.assertEqual(self._current_balance(acc1), 800.0)
        self.assertEqual(self._current_balance(acc2), 500.0)
        self.assertEqual(self._current_balance(acc3), 400.0)

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

    def test_transfer_orphan_matching(self):
        acc1 = self._make_account(name='Checking', opening_balance=1000.0)
        acc2 = self._make_account(name='Savings', opening_balance=500.0)
        acc1._sync_transfer_category()
        acc2._sync_transfer_category()
        cat2 = self.env['moneta.category'].search([('transfer_account_id', '=', acc2.id)], limit=1)

        # 1. Simulate CSV import where both accounts get their transactions first
        tx1 = self.env['moneta.transaction'].create({
            'account_id': acc1.id,
            'amount': -350.0,
            'memo': 'Bank Transfer to Savings',
        })
        tx2 = self.env['moneta.transaction'].create({
            'account_id': acc2.id,
            'amount': 350.0,
            'memo': 'Deposit from Checking',
        })

        initial_tx_count = self.env['moneta.transaction'].search_count([('account_id', 'in', [acc1.id, acc2.id])])
        self.assertEqual(initial_tx_count, 2)

        # 2. Categorize tx1 as transfer to acc2
        tx1.write({'category_id': cat2.id})

        # Check that tx1 matched existing tx2 and no 3rd transaction was created!
        final_tx_count = self.env['moneta.transaction'].search_count([('account_id', 'in', [acc1.id, acc2.id])])
        self.assertEqual(final_tx_count, 2)
        self.assertEqual(tx1.linked_transaction_id, tx2)
        self.assertEqual(tx2.linked_transaction_id, tx1)
        self.assertTrue(tx2.is_transfer)
        self.assertEqual(self._current_balance(acc1), 650.0)
        self.assertEqual(self._current_balance(acc2), 850.0)
