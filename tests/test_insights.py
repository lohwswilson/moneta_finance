# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date, timedelta
import calendar


class TestFinancialInsights(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.account = self.env['moneta.account'].create({
            'name': 'Primary Checking',
            'account_type': 'chequing',
            'opening_balance': 200.0,
        })
        self.category = self.env['moneta.category'].create({
            'name': 'Dining Out',
            'is_income': False,
        })

    def test_budget_overspend_insight(self):
        """Test budget exceeded alert generation."""
        budget = self.env['moneta.budget'].create({'name': 'Monthly Budget'})
        cat_line = self.env['moneta.budget.category'].create({
            'budget_id': budget.id,
            'category_id': self.category.id,
            'amount': 100.0,
        })

        # Create spending that exceeds budget (150 > 100)
        self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'category_id': self.category.id,
            'amount': -150.0,
            'transaction_date': date.today(),
            'state': 'cleared',
        })

        insights = self.env['moneta.insight'].get_user_insights()
        budget_insights = [i for i in insights if i['insight_type'] == 'budget']
        self.assertTrue(bool(budget_insights))
        self.assertEqual(budget_insights[0]['level'], 'danger')
        self.assertIn('Dining Out', budget_insights[0]['name'])

    def test_goal_milestone_insight(self):
        """Test goal achievement and near-completion insight."""
        goal = self.env['moneta.goal'].create({
            'name': 'Emergency Fund',
            'target_amount': 5000.0,
            'current_amount': 4800.0,
            'start_date': date(2026, 1, 1),
            'target_date': date(2026, 12, 31),
        })

        insights = self.env['moneta.insight'].get_user_insights()
        goal_insights = [i for i in insights if i['insight_type'] == 'goal']
        self.assertTrue(bool(goal_insights))
        self.assertIn('Emergency Fund', goal_insights[0]['name'])
