# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestCashflowCalendar(MonetaTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.checking_account = cls._make_account(name='Checking', account_type='checking')

    def test_cashflow_projection_simulation(self):
        """Test Quicken-style 90-day daily cashflow projection and balance simulation."""
        today = date.today()
        acc = self.checking_account
        acc.write({'opening_balance': 5000.0})
        acc._recompute_balance()

        # Create recurring salary (+4000) and rent (-2000)
        self.env['moneta.recurring.transaction'].create({
            'name': 'Monthly Salary',
            'account_id': acc.id,
            'amount': 4000.0,
            'frequency': 'monthly',
            'next_date': today + timedelta(days=15),
        })

        self.env['moneta.recurring.transaction'].create({
            'name': 'Apartment Rent',
            'account_id': acc.id,
            'amount': -2000.0,
            'frequency': 'monthly',
            'next_date': today + timedelta(days=5),
        })

        proj = self.env['moneta.cashflow.projection'].create({
            'account_id': acc.id,
            'forecast_days': '90',
            'start_date': today,
        })

        self.assertEqual(proj.starting_balance, 5000.0)
        self.assertGreater(proj.total_projected_income, 0.0)
        self.assertGreater(proj.total_projected_expenses, 0.0)
        self.assertFalse(proj.has_overdraft_risk)
        self.assertEqual(len(proj.line_ids), 91)

    def test_cashflow_overdraft_detection(self):
        """Test overdraft risk detection when projected outflows exceed liquidity."""
        today = date.today()
        acc = self.checking_account
        acc.write({'opening_balance': 500.0})
        acc._recompute_balance()

        # Create large bill exceeding balance
        self.env['moneta.recurring.transaction'].create({
            'name': 'Huge Tax Payment',
            'account_id': acc.id,
            'amount': -2500.0,
            'frequency': 'monthly',
            'next_date': today + timedelta(days=10),
        })

        proj = self.env['moneta.cashflow.projection'].create({
            'account_id': acc.id,
            'forecast_days': '30',
            'start_date': today,
        })

        self.assertTrue(proj.has_overdraft_risk)
        self.assertGreater(proj.overdraft_days_count, 0)
        self.assertLess(proj.lowest_projected_balance, 0.0)
