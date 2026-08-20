# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date


class TestLoanAndSimulations(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.currency = self.env.company.currency_id

    def test_loan_scenario_calculation(self):
        """Test loan amortization calculation and interest savings."""
        scenario = self.env['moneta.loan.scenario'].create({
            'name': 'Mortgage 300k 30yr',
            'principal_amount': 300000.0,
            'annual_interest_rate': 6.0,
            'loan_term_years': 30,
            'start_date': date(2026, 1, 1),
            'extra_monthly_payment': 200.0,
        })
        
        # Monthly payment for 300k at 6% over 30 yrs is approx $1,798.65
        self.assertAlmostEqual(scenario.monthly_payment, 1798.65, delta=1.0)
        self.assertGreater(scenario.interest_saved, 0.0)
        self.assertGreater(scenario.years_saved, 0.0)

        # Generate schedule lines
        scenario.action_generate_schedule()
        self.assertGreater(len(scenario.line_ids), 0)
        first_line = scenario.line_ids[0]
        self.assertEqual(first_line.payment_number, 1)
        self.assertAlmostEqual(first_line.interest_amount, 1500.0, delta=1.0)

    def test_monte_carlo_simulation(self):
        """Test Monte Carlo stochastic simulation execution."""
        sim = self.env['moneta.monte.carlo'].create({
            'name': 'Retirement Sim Test',
            'starting_portfolio_value': 500000.0,
            'annual_savings_contribution': 30000.0,
            'years_to_retirement': 10,
            'years_in_retirement': 25,
            'annual_retirement_spend': 60000.0,
            'equity_allocation_pct': 80.0,
            'bond_allocation_pct': 20.0,
        })
        
        sim.action_run_simulation()
        self.assertEqual(sim.simulations_count, 1000)
        self.assertGreaterEqual(sim.success_probability_pct, 0.0)
        self.assertLessEqual(sim.success_probability_pct, 100.0)
        self.assertEqual(len(sim.path_ids), 36) # 0 to 35 years

    def test_account_loan_scenario_metrics(self):
        """Test that moneta.account properly exposes linked loan scenario metrics."""
        account = self.env['moneta.account'].create({
            'name': 'Primary Mortgage',
            'account_type': 'mortgage',
            'opening_balance': -250000.0,
            'current_balance': -250000.0,
            'interest_rate': 5.5,
        })
        scenario = self.env['moneta.loan.scenario'].create({
            'name': 'Primary Mortgage Scenario',
            'account_id': account.id,
            'principal_amount': 250000.0,
            'annual_interest_rate': 5.5,
            'loan_term_years': 30,
            'start_date': date(2026, 1, 1),
        })
        account._compute_loan_metrics()
        self.assertEqual(account.loan_scenario_id, scenario)
        self.assertAlmostEqual(account.loan_monthly_payment, scenario.monthly_payment, places=2)
        self.assertTrue(account.loan_payoff_date)
        self.assertGreater(account.loan_remaining_interest, 0.0)

    def test_rate_change_inference(self):
        """Test automatic rate change detection from split interest payments."""
        account = self.env['moneta.account'].create({
            'name': 'Adjustable Rate Loan',
            'account_type': 'loan',
            'opening_balance': -200000.0,
            'current_balance': -200000.0,
            'interest_rate': 4.0,
        })
        scenario = self.env['moneta.loan.scenario'].create({
            'name': 'Adjustable Loan Scenario',
            'account_id': account.id,
            'principal_amount': 200000.0,
            'annual_interest_rate': 4.0,
            'loan_term_years': 25,
            'start_date': date(2026, 1, 1),
        })
        cat_int = self.env['moneta.category'].create({'name': 'Loan Interest', 'is_income': False})
        cat_prin = self.env['moneta.category'].create({'name': 'Principal', 'is_income': False})

        # Month 1: 4.0% rate ($200k bal -> ~$666.67 interest)
        self.env['moneta.transaction'].create({
            'account_id': account.id,
            'transaction_date': date(2026, 1, 15),
            'amount': -1500.0,
            'is_split': True,
            'split_ids': [
                (0, 0, {'category_id': cat_int.id, 'amount': -666.67}),
                (0, 0, {'category_id': cat_prin.id, 'amount': -833.33}),
            ]
        })
        # Month 2: 4.0% rate
        self.env['moneta.transaction'].create({
            'account_id': account.id,
            'transaction_date': date(2026, 2, 15),
            'amount': -1500.0,
            'is_split': True,
            'split_ids': [
                (0, 0, {'category_id': cat_int.id, 'amount': -663.89}),
                (0, 0, {'category_id': cat_prin.id, 'amount': -836.11}),
            ]
        })
        # Month 3: Rate hikes to 5.5% ($198k bal -> ~$907.50 interest)
        self.env['moneta.transaction'].create({
            'account_id': account.id,
            'transaction_date': date(2026, 3, 15),
            'amount': -1700.0,
            'is_split': True,
            'split_ids': [
                (0, 0, {'category_id': cat_int.id, 'amount': -907.50}),
                (0, 0, {'category_id': cat_prin.id, 'amount': -792.50}),
            ]
        })
        # Month 4: 5.5% rate
        self.env['moneta.transaction'].create({
            'account_id': account.id,
            'transaction_date': date(2026, 4, 15),
            'amount': -1700.0,
            'is_split': True,
            'split_ids': [
                (0, 0, {'category_id': cat_int.id, 'amount': -903.87}),
                (0, 0, {'category_id': cat_prin.id, 'amount': -796.13}),
            ]
        })

        res = scenario.action_infer_rate_changes()
        self.assertEqual(res['type'], 'ir.actions.client')
        self.assertAlmostEqual(scenario.annual_interest_rate, 4.0, delta=0.2)
        # Should have detected the step to 5.5% on 2026-03-15
        self.assertTrue(scenario.rate_change_ids)
        step = scenario.rate_change_ids[0]
        self.assertEqual(step.effective_date, date(2026, 3, 15))
        self.assertAlmostEqual(step.annual_rate, 5.5, delta=0.3)
