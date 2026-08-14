# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestDashboard(MonetaTestBase):
    """Dashboard tiles are per-user (record rules scope every compute search to
    the owner). Tests run under a dedicated user so demo data owned by other
    users never leaks into the assertions."""

    def _dash_user(self):
        return self._make_user('Dash User', 'dash_user')

    def _dash(self, user):
        # The dashboard record + its computes run in the user's env.
        return self.env['moneta.dashboard'].with_user(user).create({})

    def test_net_worth_assets_minus_liabilities(self):
        user = self._dash_user()
        self._make_account(user=user, name='Checking', account_type='checking', opening_balance=1000.0)
        self._make_account(user=user, name='Visa', account_type='credit_card', opening_balance=-500.0)
        self._make_account(user=user, name='Car Loan', account_type='loan', opening_balance=-2500.0)
        self.assertEqual(self._dash(user).net_worth, -2000.0)

    def test_net_worth_respects_exclude_flag(self):
        user = self._dash_user()
        self._make_account(user=user, name='Checking', account_type='checking', opening_balance=1000.0)
        hidden = self._make_account(user=user, name='Hidden', account_type='asset', opening_balance=9999.0)
        hidden.write({'exclude_from_net_worth': True})
        self.assertEqual(self._dash(user).net_worth, 1000.0)

    def test_month_income_and_expenses(self):
        user = self._dash_user()
        acc = self._make_account(user=user, opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        self._make_transaction(acc, 2500.0, user=user, transaction_date=today, state='cleared')
        self._make_transaction(acc, -40.0, user=user, transaction_date=today, state='cleared')
        self._make_transaction(acc, -60.0, user=user, transaction_date=today, state='cleared')
        # A void transaction is excluded.
        self._make_transaction(acc, -500.0, user=user, transaction_date=today, state='void')
        dash = self._dash(user)
        self.assertEqual(dash.month_income, 2500.0)
        self.assertEqual(dash.month_expenses, 100.0)

    def test_upcoming_bills_from_recurring(self):
        user = self._dash_user()
        acc = self._make_account(user=user, opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        Recurring = self.env['moneta.recurring.transaction'].with_user(user)
        Recurring.create({
            'name': 'Rent',
            'account_id': acc.id,
            'amount': -1200.0,
            'frequency': 'monthly',
            'next_date': today,
        })
        Recurring.create({
            'name': 'Salary',
            'account_id': acc.id,
            'amount': 3500.0,  # income, not a bill
            'frequency': 'monthly',
            'next_date': today,
        })
        dash = self._dash(user)
        self.assertEqual(dash.upcoming_bill_count, 1)
        self.assertEqual(dash.upcoming_bills_total, 1200.0)