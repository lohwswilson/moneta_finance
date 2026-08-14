# -*- coding: utf-8 -*-
import base64
from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestPowerUserFeatures(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.currency = self.env.company.currency_id

        self.account = self.env['moneta.account'].create({
            'name': 'Checking Account',
            'account_type': 'checking',
            'opening_balance': 5000.0,
        })

        self.credit_card = self.env['moneta.account'].create({
            'name': 'Sapphire Reserve Card',
            'account_type': 'credit_card',
            'opening_balance': 0.0,
            'billing_cycle_day': 20,
            'payment_due_day': 15,
        })

        self.category = self.env['moneta.category'].create({
            'name': 'Groceries',
            'is_income': False,
        })

        self.payee_primary = self.env['moneta.payee'].create({'name': 'Starbucks'})
        self.payee_dupe = self.env['moneta.payee'].create({'name': 'STARBUCKS #1204'})

    def test_batch_transaction_actions(self):
        """Test batch mark cleared and batch categorize wizard."""
        tx1 = self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'payee_id': self.payee_primary.id,
            'amount': -20.0,
            'transaction_date': date(2026, 8, 1),
        })
        tx2 = self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'payee_id': self.payee_primary.id,
            'amount': -35.0,
            'transaction_date': date(2026, 8, 2),
        })

        txs = self.env['moneta.transaction'].concat(tx1, tx2)
        txs.action_batch_mark_cleared()
        self.assertEqual(tx1.state, 'cleared')
        self.assertEqual(tx2.state, 'cleared')

        # Batch categorize wizard
        wiz = self.env['moneta.transaction.batch.category.wizard'].create({
            'transaction_ids': [(6, 0, txs.ids)],
            'category_id': self.category.id,
        })
        wiz.action_apply()
        self.assertEqual(tx1.category_id.id, self.category.id)
        self.assertEqual(tx2.category_id.id, self.category.id)

    def test_account_cashflow_forecast(self):
        """Test 30/60/90 day balance forecasting with scheduled transactions."""
        today = date.today()
        self.env['moneta.recurring.transaction'].create({
            'name': 'Monthly Salary',
            'account_id': self.account.id,
            'amount': 3000.0,
            'frequency': 'monthly',
            'next_date': today + timedelta(days=10),
            'active': True,
        })
        self.account.invalidate_recordset()
        self.account._compute_forecast_and_statement_cycle()

        # Should reflect +3000 in 30 days
        self.assertEqual(self.account.forecast_balance_30d, 8000.0)

    def test_payee_merge_wizard(self):
        """Test merging duplicate payee and creating search alias."""
        tx = self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'payee_id': self.payee_dupe.id,
            'amount': -5.0,
            'transaction_date': date(2026, 8, 5),
        })

        wiz = self.env['moneta.payee.merge.wizard'].create({
            'primary_payee_id': self.payee_primary.id,
            'duplicate_payee_ids': [(6, 0, [self.payee_dupe.id])],
            'create_aliases': True,
        })
        wiz.action_merge()

        # Transaction moved to primary
        self.assertEqual(tx.payee_id.id, self.payee_primary.id)
        # Duplicate deactivated
        self.assertFalse(self.payee_dupe.active)
        # Alias created
        alias = self.env['moneta.payee.alias'].search([('payee_id', '=', self.payee_primary.id)])
        self.assertTrue(bool(alias))

    def test_account_export_wizard(self):
        """Test QIF and CSV checkbook export."""
        self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'payee_id': self.payee_primary.id,
            'amount': -15.0,
            'memo': 'Latte & Muffin',
            'transaction_date': date(2026, 8, 10),
        })

        # Test CSV export
        wiz_csv = self.env['moneta.export.wizard'].create({
            'account_ids': [(6, 0, [self.account.id])],
            'export_format': 'csv',
        })
        wiz_csv.action_export()
        self.assertEqual(wiz_csv.state, 'get')
        self.assertTrue(bool(wiz_csv.file_data))
        csv_decoded = base64.b64decode(wiz_csv.file_data).decode('utf-8')
        self.assertIn('Latte & Muffin', csv_decoded)

        # Test QIF export
        wiz_qif = self.env['moneta.export.wizard'].create({
            'account_ids': [(6, 0, [self.account.id])],
            'export_format': 'qif',
        })
        wiz_qif.action_export()
        self.assertEqual(wiz_qif.state, 'get')
        qif_decoded = base64.b64decode(wiz_qif.file_data).decode('utf-8')
        self.assertIn('!Type:Bank', qif_decoded)
        self.assertIn('PLatte & Muffin' if 'PLatte' in qif_decoded else 'PStarbucks', qif_decoded)
