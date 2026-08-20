# -*- coding: utf-8 -*-
from datetime import date
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestActionHistory(MonetaTestBase):

    def test_log_and_undo_create_transaction(self):
        """Test logging a created transaction and cleanly reverting it."""
        acc = self._make_account(name='Checking', account_type='checking')
        tx = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'transaction_date': date(2026, 8, 1),
            'amount': -50.0,
            'memo': 'Coffee',
        })
        # Log creation
        log = self.env['moneta.action.history'].log_action(
            description='Created transaction Coffee ($50.00)',
            entity_type='transaction',
            action='create',
            entity_id=tx.id,
            after_data={'ids': [tx.id]},
        )
        self.assertFalse(log.is_undone)
        self.assertTrue(tx.exists())

        # Undo action
        res = log.action_undo()
        self.assertEqual(res['type'], 'ir.actions.client')
        self.assertTrue(log.is_undone)
        self.assertTrue(log.undone_at)
        self.assertFalse(tx.exists(), "Transaction must be deleted on undo")

    def test_log_and_undo_update_transaction(self):
        """Test logging an update mutation and restoring previous state."""
        acc = self._make_account(name='Checking', account_type='checking')
        cat_food = self.env['moneta.category'].create({'name': 'Food'})
        cat_utils = self.env['moneta.category'].create({'name': 'Utilities'})
        tx = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'transaction_date': date(2026, 8, 1),
            'amount': -120.0,
            'category_id': cat_food.id,
        })

        # Update category from Food to Utilities
        before_state = {'records': [{'id': tx.id, 'category_id': cat_food.id}]}
        tx.write({'category_id': cat_utils.id})
        after_state = {'records': [{'id': tx.id, 'category_id': cat_utils.id}]}

        log = self.env['moneta.action.history'].log_action(
            description='Updated transaction category to Utilities',
            entity_type='transaction',
            action='update',
            entity_id=tx.id,
            before_data=before_state,
            after_data=after_state,
        )

        self.assertEqual(tx.category_id, cat_utils)

        # Undo
        log.action_undo()
        self.assertTrue(log.is_undone)
        self.assertEqual(tx.category_id, cat_food, "Category must be restored to Food")

    def test_undo_last_action(self):
        """Test 1-click undo last action helper."""
        acc = self._make_account(name='Checking', account_type='checking')
        tx = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'transaction_date': date(2026, 8, 1),
            'amount': -35.0,
            'memo': 'Lunch',
        })
        log = self.env['moneta.action.history'].log_action(
            description='Created lunch transaction',
            entity_type='transaction',
            action='create',
            entity_id=tx.id,
            after_data={'ids': [tx.id]},
        )

        self.env['moneta.action.history'].action_undo_last()
        self.assertTrue(log.is_undone)
        self.assertFalse(tx.exists())

    def test_cannot_undo_twice(self):
        """Test that already undone actions cannot be undone again."""
        acc = self._make_account(name='Checking', account_type='checking')
        tx = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'transaction_date': date(2026, 8, 1),
            'amount': -10.0,
        })
        log = self.env['moneta.action.history'].log_action(
            description='Test transaction',
            entity_type='transaction',
            action='create',
            entity_id=tx.id,
            after_data={'ids': [tx.id]},
        )
        log.action_undo()
        with self.assertRaises(UserError):
            log.action_undo()
