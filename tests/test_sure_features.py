# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestSureFeatures(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.currency = self.env.company.currency_id

        self.account = self.env['moneta.account'].create({
            'name': 'Checking Account',
            'account_type': 'checking',
            'opening_balance': 5000.0,
        })

        self.category = self.env['moneta.category'].create({
            'name': 'Coffee & Cafes',
            'is_income': False,
        })

        self.payee = self.env['moneta.payee'].create({
            'name': 'Starbucks Coffee',
        })

    def test_transaction_rule_engine(self):
        """Test rule matching and retroactive application."""
        rule = self.env['moneta.transaction.rule'].create({
            'name': 'Starbucks Coffee Rule',
            'match_payee_type': 'contains',
            'match_payee_text': 'starbucks',
            'set_category_id': self.category.id,
            'set_state': 'cleared',
        })

        tx = self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'payee_id': self.payee.id,
            'amount': -6.50,
            'transaction_date': date(2026, 8, 1),
        })

        # Rule should have matched on create
        self.assertEqual(tx.category_id.id, self.category.id)
        self.assertEqual(tx.state, 'cleared')

        # Test retroactive apply action
        rule.action_apply_retroactive()
        self.assertEqual(tx.category_id.id, self.category.id)

    def test_financial_goal(self):
        """Test goal calculations and contribution wizard."""
        goal = self.env['moneta.goal'].create({
            'name': 'Hawaii Vacation',
            'target_amount': 6000.0,
            'current_amount': 2000.0,
            'start_date': date(2026, 1, 1),
            'target_date': date(2026, 12, 31),
        })

        self.assertAlmostEqual(goal.progress_percent, 33.3, delta=0.5)
        self.assertEqual(goal.remaining_amount, 4000.0)
        self.assertEqual(goal.status, 'in_progress')

        # Test wizard fund deposit
        wiz = self.env['moneta.goal.fund.wizard'].create({
            'goal_id': goal.id,
            'action_type': 'deposit',
            'amount': 4000.0,
        })
        wiz.action_apply()
        self.assertEqual(goal.current_amount, 6000.0)
        self.assertEqual(goal.status, 'achieved')
