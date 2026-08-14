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
