# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestCPFAndSRS(MonetaTestBase):

    def test_cpf_account_creation_and_defaults(self):
        """Test CPF account types, interest rate auto-configuration, and is_cpf flag."""
        oa = self.env['moneta.account'].create({
            'name': 'My CPF OA',
            'account_type': 'cpf_oa',
            'opening_balance': 50000.0,
            'interest_rate': 2.50,
        })
        sa = self.env['moneta.account'].create({
            'name': 'My CPF SA',
            'account_type': 'cpf_sa',
            'opening_balance': 80000.0,
            'interest_rate': 4.00,
        })
        self.assertTrue(oa.is_cpf)
        self.assertEqual(oa.cpf_account_type, 'oa')
        self.assertEqual(oa.interest_rate, 2.50)

        self.assertTrue(sa.is_cpf)
        self.assertEqual(sa.cpf_account_type, 'sa')
        self.assertEqual(sa.interest_rate, 4.00)

    def test_cpf_monthly_lowest_balance_interest(self):
        """Test CPF lowest-balance monthly interest calculation rule."""
        oa = self.env['moneta.account'].create({
            'name': 'CPF OA Test',
            'account_type': 'cpf_oa',
            'opening_balance': 12000.0,
            'interest_rate': 2.50,
        })
        # In March 2026, add $3,000 on March 5, then withdraw $5,000 on March 20 (lowest balance = $10,000)
        self.env['moneta.transaction'].create({
            'account_id': oa.id,
            'transaction_date': date(2026, 3, 5),
            'amount': 3000.0,
        })
        self.env['moneta.transaction'].create({
            'account_id': oa.id,
            'transaction_date': date(2026, 3, 20),
            'amount': -5000.0,
        })

        res = oa.calculate_monthly_cpf_interest(year=2026)
        self.assertEqual(res['account_id'], oa.id)
        self.assertGreater(res['total_annual_interest'], 0)
        march_entry = next(m for m in res['monthly_breakdown'] if 'March 2026' in m['month'])
        self.assertEqual(march_entry['lowest_balance'], 10000.0)
        # Interest on $10,000 at 2.5% p.a. for 1 month = 10000 * 0.025 / 12 = $20.83
        self.assertAlmostEqual(march_entry['interest_earned'], 20.83, delta=0.05)

    def test_cpf_life_simulator(self):
        """Test CPF LIFE Retirement Payout Simulator for Standard & Escalating plans."""
        sim = self.env['moneta.cpf.life.simulator'].create({
            'name': 'Wilson CPF LIFE Plan',
            'birth_year': 1970,
            'ra_balance_at_55': 213000.0,  # Full Retirement Sum (FRS)
            'plan_type': 'standard',
            'payout_start_age': '65',
        })
        self.assertEqual(sim.retirement_sum_tier, 'frs')
        self.assertGreaterEqual(sim.monthly_payout_estimated, 1600.0)
        self.assertLessEqual(sim.monthly_payout_estimated, 1750.0)
        self.assertGreater(sim.cumulative_payout_85, 350000.0)

        # Switch to escalating plan (+2% annual increase)
        sim.write({'plan_type': 'escalating'})
        self.assertGreater(sim.payout_at_80, sim.monthly_payout_estimated)
        self.assertGreater(sim.payout_at_90, sim.payout_at_80)

    def test_srs_tax_relief_and_withdrawal_tracker(self):
        """Test Singapore SRS annual caps ($15.3k) and 10-year penalty-free withdrawal."""
        srs_acc = self.env['moneta.account'].create({
            'name': 'DBS SRS Account',
            'account_type': 'srs',
            'opening_balance': 0.0,
        })
        # Deposit $15,300 into SRS
        self.env['moneta.transaction'].create({
            'account_id': srs_acc.id,
            'transaction_date': date(2026, 6, 15),
            'amount': 15300.0,
            'memo': 'SRS Year-End Contribution',
        })

        tracker = self.env['moneta.srs.tracker'].create({
            'tax_year': 2026,
            'residency_status': 'citizen_pr',
            'marginal_tax_rate': '15.0',
            'srs_account_id': srs_acc.id,
        })

        self.assertEqual(tracker.annual_cap, 15300.0)
        self.assertEqual(tracker.total_contributed, 15300.0)
        self.assertEqual(tracker.remaining_allowance, 0.0)
        # Tax saved = 15300 * 15% = $2,295.00
        self.assertEqual(tracker.estimated_tax_savings, 2295.00)

        # 10-year withdrawal optimization
        # $15,300 over 10 years = $1,530 / year -> 50% taxable = $765 / year (<= $20,000 tax-free)
        self.assertEqual(tracker.annual_withdrawal_target, 1530.0)
        self.assertEqual(tracker.annual_taxable_portion, 765.0)
        self.assertTrue(tracker.is_tax_free_strategy)
