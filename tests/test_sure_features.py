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

    def test_property_home_equity(self):
        """Test real estate market value, mortgage debt, and equity calculations."""
        mortgage = self.env['moneta.account'].create({
            'name': 'Home Mortgage',
            'account_type': 'mortgage',
            'opening_balance': -400000.0,
        })

        prop = self.env['moneta.property'].create({
            'name': 'Primary Residence',
            'property_type': 'primary_residence',
            'current_market_value': 600000.0,
            'mortgage_account_id': mortgage.id,
        })

        self.assertEqual(prop.mortgage_balance, 400000.0)
        self.assertEqual(prop.equity_value, 200000.0)
        self.assertAlmostEqual(prop.loan_to_value_ratio, 66.7, delta=0.5)

        # Make a mortgage payment of ,000 to reduce debt
        self.env['moneta.transaction'].create({
            'account_id': mortgage.id,
            'amount': 50000.0,
            'state': 'cleared',
        })
        self.assertEqual(mortgage.current_balance, -350000.0)
        # Property equity should dynamically update to ,000
        self.assertEqual(prop.mortgage_balance, 350000.0)
        self.assertEqual(prop.equity_value, 250000.0)
        self.assertAlmostEqual(prop.loan_to_value_ratio, 58.3, delta=0.5)

    def test_vehicle_and_antique_tracking(self):
        """Test vehicle specifications, antique details, and valuation log."""
        car = self.env['moneta.property'].create({
            'name': '2024 Tesla Model Y',
            'asset_category': 'vehicle',
            'property_type': 'automobile',
            'vehicle_make': 'Tesla',
            'vehicle_model': 'Model Y',
            'vehicle_year': 2024,
            'vehicle_vin': '5YJSA1E28HF123456',
            'vehicle_mileage': 14500,
            'current_market_value': 41000.0,
        })
        self.assertEqual(car.asset_category, 'vehicle')
        self.assertEqual(car.vehicle_vin, '5YJSA1E28HF123456')

        # Antique & Valuables
        clock = self.env['moneta.property'].create({
            'name': '19th Century French Ormolu Clock',
            'asset_category': 'antiques',
            'property_type': 'antique_furniture',
            'antique_era': 'Victorian 1870',
            'maker_artist': 'Raingo Frères',
            'condition_grade': 'excellent',
            'current_market_value': 8200.0,
        })
        self.assertEqual(clock.asset_category, 'antiques')
        self.assertEqual(clock.condition_grade, 'excellent')

        # Valuation log
        self.env['moneta.property.valuation'].create({
            'property_id': clock.id,
            'valuation_date': date(2026, 8, 1),
            'appraised_value': 8200.0,
            'appraiser': "Sotheby's Appraisal Service",
        })
        self.assertEqual(len(clock.valuation_line_ids), 1)
        self.assertEqual(clock.valuation_line_ids[0].appraised_value, 8200.0)
