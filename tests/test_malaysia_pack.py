# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestMalaysiaPack(MonetaTestBase):

    def test_epf_3_account_structure_and_isaraan(self):
        """Test Malaysia EPF 3-Account restructuring, dividend projection, and i-Saraan matching."""
        epf = self.env['moneta.epf.account'].create({
            'name': 'Wilson KWSP Savings',
            'scheme_type': 'conventional',
            'account_1_persaraan': 150000.0,
            'account_2_sejahtera': 30000.0,
            'account_3_fleksibel': 20000.0,
            'projected_dividend_rate': 5.5,
            'i_saraan_voluntary_ytd': 4000.0,
        })

        # Total = 150k + 30k + 20k = 200k
        self.assertEqual(epf.total_epf_balance, 200000.0)
        # Dividend = 200k * 5.5% = 11,000
        self.assertEqual(epf.projected_annual_dividend, 11000.0)
        # i-Saraan matching: 15% of 4000 = 600, capped at 500
        self.assertEqual(epf.i_saraan_matching_incentive, 500.0)

        # Monthly contribution of RM2,000
        tx = self.env['moneta.epf.transaction'].create({
            'epf_account_id': epf.id,
            'transaction_type': 'monthly_salary_contribution',
            'amount_total': 2000.0,
        })
        self.assertEqual(tx.amount_account_1, 1500.0)  # 75%
        self.assertEqual(tx.amount_account_2, 300.0)   # 15%
        self.assertEqual(tx.amount_account_3, 200.0)   # 10%

    def test_lhdn_tax_planner_and_reliefs(self):
        """Test Malaysia LHDN Borang BE tax calculation and statutory reliefs."""
        planner = self.env['moneta.lhdn.tax.planner'].create({
            'tax_year': '2025',
            'annual_employment_income': 120000.0,
            'relief_life_insurance': 3000.0,
            'relief_epf': 4000.0,
            'relief_lifestyle': 2500.0,
            'relief_sspn': 8000.0,
            'relief_medical_expenses': 5000.0,
            'monthly_pcb_deducted': 8000.0,
        })
        planner._compute_lhdn_tax()

        # Total Reliefs: 9,000 (Individual) + 3,000 (Life) + 4,000 (EPF) + 2,500 (Lifestyle) + 8,000 (SSPN) + 5,000 (Medical) = 31,500
        self.assertEqual(planner.total_tax_reliefs, 31500.0)
        # Chargeable income = 120,000 - 31,500 = 88,500
        self.assertEqual(planner.chargeable_income, 88500.0)
        self.assertEqual(planner.marginal_tax_bracket_pct, 19.0)

        # Tax on 88,500 = 3,700 (first 70k) + (88,500 - 70,000) * 19% (3,515) = 7,215
        self.assertEqual(planner.gross_tax_payable, 7215.0)
        self.assertEqual(planner.net_tax_payable, 7215.0)
        # Refund = PCB (8,000) - Tax (7,215) = 785
        self.assertEqual(planner.tax_refund_or_payable, 785.0)

    def test_malaysia_flexi_loan_and_rpgt(self):
        """Test Malaysian flexi-home loan interest offset and RPGT capital gains tax."""
        # 1. Flexi Loan
        loan = self.env['moneta.malaysia.flexi.loan'].create({
            'name': 'Maybank MaxiHome Flexi',
            'outstanding_principal': 500000.0,
            'standardised_base_rate': 3.00,
            'bank_spread_rate': 1.15,
            'flexi_deposit_balance': 100000.0,
        })
        self.assertEqual(loan.effective_interest_rate, 4.15)
        self.assertEqual(loan.net_chargeable_principal, 400000.0)
        # Annual savings: 100,000 * 4.15% = 4,150
        self.assertEqual(loan.annual_interest_saved, 4150.0)

        # 2. RPGT Calculator
        rpgt = self.env['moneta.rpgt.calculator'].create({
            'citizenship_status': 'citizen_pr',
            'acquisition_date': date(2021, 1, 1),
            'disposal_date': date(2023, 1, 1),  # 2 years holding -> 30% RPGT tier
            'acquisition_price': 500000.0,
            'disposal_price': 700000.0,
            'allowable_expenses': 20000.0,
        })
        # Gross gain: 700,000 - 520,000 = 180,000
        self.assertEqual(rpgt.gross_chargeable_gain, 180000.0)
        self.assertEqual(rpgt.rpgt_rate_pct, 30.0)
        # Exemption: 10% of 180k = 18,000
        self.assertEqual(rpgt.individual_exemption_amount, 18000.0)
        # Net gain: 180,000 - 18,000 = 162,000
        self.assertEqual(rpgt.net_chargeable_gain, 162000.0)
        # Tax: 162,000 * 30% = 48,600
        self.assertEqual(rpgt.rpgt_tax_payable, 48600.0)
