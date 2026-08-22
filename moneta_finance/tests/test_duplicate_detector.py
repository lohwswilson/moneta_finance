# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestDuplicateDetector(MonetaTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.checking_account = cls._make_account(name='Checking', account_type='checking')

    def test_duplicate_transaction_scan_and_merge(self):
        """Test scanning for duplicate transactions and 1-click merging."""
        today = date.today()
        acc = self.checking_account

        # Create two identical transactions on same account and date
        tx1 = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'transaction_date': today,
            'amount': -125.50,
            'memo': 'Original Grocery Store',
        })

        tx2 = self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'transaction_date': today,
            'amount': -125.50,
            'memo': 'Duplicate Imported Entry',
        })

        wiz = self.env['moneta.duplicate.detector.wizard'].create({
            'account_id': acc.id,
            'date_tolerance_days': 2,
            'match_exact_amount': True,
        })
        wiz.action_scan_duplicates()

        self.assertEqual(len(wiz.candidate_line_ids), 1)
        self.assertEqual(wiz.duplicate_count, 1)

        # Merge duplicates
        wiz.action_merge_selected_duplicates()

        # tx1 should remain with combined memo, tx2 should be deleted
        self.assertTrue(tx1.exists())
        self.assertFalse(tx2.exists())
        self.assertIn('Original Grocery Store', tx1.memo)
        self.assertIn('Duplicate Imported Entry', tx1.memo)
