# -*- coding: utf-8 -*-
from datetime import date
from .common import MonetaTestBase


class TestPayeeAnalytics(MonetaTestBase):
    """Test payee financial analytics, YoY spending, and cadence detection (v1.14.0)."""

    def setUp(self):
        super().setUp()
        self.account = self._make_account(name='Checking Account')
        self.payee = self.env['moneta.payee'].create({
            'name': 'Netflix Subscription',
            'website': 'https://netflix.com',
        })

    def test_payee_spending_and_cadence(self):
        """Transactions across dates compute YoY spend and detect monthly cadence."""
        today = date.today()
        # Create 3 transactions spaced roughly 30 days apart
        d1 = today.replace(day=1)
        # 1 month ago
        d2 = (d1.replace(day=1) - date.resolution).replace(day=1)
        # 2 months ago
        d3 = (d2 - date.resolution).replace(day=1)

        self._make_transaction(self.account, -15.99, payee_id=self.payee.id, category_id=self.cat_expense.id, transaction_date=d3)
        self._make_transaction(self.account, -15.99, payee_id=self.payee.id, category_id=self.cat_expense.id, transaction_date=d2)
        self._make_transaction(self.account, -15.99, payee_id=self.payee.id, category_id=self.cat_expense.id, transaction_date=d1)

        self.payee.invalidate_recordset()
        self.assertEqual(self.payee.transaction_count, 3)
        self.assertAlmostEqual(self.payee.avg_transaction_amount, 15.99, places=2)
        self.assertEqual(self.payee.detected_cadence, 'monthly')
        self.assertEqual(self.payee.suggested_category_id, self.cat_expense)

    def test_empty_payee_analytics(self):
        """Payee with no transactions returns safe zeroed metrics."""
        fresh_payee = self.env['moneta.payee'].create({'name': 'Unused Store'})
        fresh_payee.invalidate_recordset()

        self.assertEqual(fresh_payee.transaction_count, 0)
        self.assertEqual(fresh_payee.spent_this_year, 0.0)
        self.assertEqual(fresh_payee.spent_prior_year, 0.0)
        self.assertEqual(fresh_payee.detected_cadence, 'none')
        self.assertFalse(fresh_payee.suggested_category_id)
