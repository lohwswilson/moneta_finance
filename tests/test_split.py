# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestSplit(MonetaTestBase):

    def test_split_sum_must_match_parent(self):
        acc = self._make_account(opening_balance=0.0)
        with self.assertRaises(ValidationError):
            self.env['moneta.transaction'].create({
                'account_id': acc.id,
                'amount': -100.0,
                'is_split': True,
                'state': 'cleared',
                'split_ids': [
                    (0, 0, {'category_id': self.cat_expense.id, 'amount': -30.0}),
                    (0, 0, {'category_id': self.cat_expense.id, 'amount': -50.0}),
                ],
            })

    def test_split_sum_matching_creates_transaction(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'amount': -100.0,
            'is_split': True,
            'state': 'cleared',
            'split_ids': [
                (0, 0, {'category_id': self.cat_expense.id, 'amount': -60.0}),
                (0, 0, {'category_id': self.cat_expense.id, 'amount': -40.0}),
            ],
        })
        self.assertEqual(len(tx.split_ids), 2)
        # A split parent carries no category on its own line.
        self.assertFalse(tx.category_id)
        # The parent contributes its amount to the balance once (children are
        # a separate model and are never summed into the balance).
        self.assertEqual(self._current_balance(acc), -100.0)