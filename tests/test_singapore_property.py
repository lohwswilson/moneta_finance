# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestSingaporeProperty(MonetaTestBase):

    def test_cpf_housing_accrued_interest_simulation(self):
        """Test CPF Housing Accrued Interest (2.5% compounded) and resale net proceeds."""
        sim = self.env['moneta.cpf.accrued.interest'].create({
            'name': 'Punggol 4-Room BTO Resale',
            'purchase_price': 500000.0,
            'cpf_downpayment': 100000.0,
            'cpf_grants': 45000.0,
            'monthly_cpf_payment': 1200.0,
            'holding_period_years': 5.0,
            'projected_selling_price': 750000.0,
            'outstanding_loan_balance': 250000.0,
            'estimated_resale_fees': 18750.0,
        })

        # Principal = 100k + 45k + (1200 * 12 * 5) = 145k + 72k = 217,000
        self.assertEqual(sim.total_cpf_principal, 217000.0)
        self.assertGreater(sim.total_cpf_accrued_interest, 20000.0)
        self.assertGreater(sim.total_cpf_refund_to_oa, 237000.0)
        self.assertFalse(sim.is_negative_cash_sale)
        self.assertGreater(sim.net_cash_in_hand, 200000.0)

    def test_stamp_duty_bsd_and_absd(self):
        """Test Singapore Buyer's Stamp Duty (BSD) and ABSD progressive rates."""
        # 1. Singapore Citizen 1st Property ($1,200,000)
        # BSD: 180k*1% (1800) + 180k*2% (3600) + 640k*3% (19200) + 200k*4% (8000) = $32,600
        afford_sc1 = self.env['moneta.singapore.property.affordability'].create({
            'name': 'SC First Home',
            'property_price': 1200000.0,
            'property_type': 'residential',
            'buyer_profile': 'sc_first',
        })
        self.assertEqual(afford_sc1.bsd_amount, 32600.0)
        self.assertEqual(afford_sc1.absd_rate_pct, 0.0)
        self.assertEqual(afford_sc1.absd_amount, 0.0)
        self.assertEqual(afford_sc1.total_stamp_duty, 32600.0)

        # 2. Singapore Citizen 2nd Property (20% ABSD)
        afford_sc2 = self.env['moneta.singapore.property.affordability'].create({
            'name': 'SC Second Home',
            'property_price': 1200000.0,
            'property_type': 'residential',
            'buyer_profile': 'sc_second',
        })
        self.assertEqual(afford_sc2.absd_rate_pct, 20.0)
        self.assertEqual(afford_sc2.absd_amount, 240000.0)
        self.assertEqual(afford_sc2.total_stamp_duty, 272600.0)

        # 3. Foreigner (60% ABSD)
        afford_for = self.env['moneta.singapore.property.affordability'].create({
            'name': 'Foreigner Luxury Condo',
            'property_price': 2000000.0,
            'property_type': 'residential',
            'buyer_profile': 'foreigner',
        })
        self.assertEqual(afford_for.absd_rate_pct, 60.0)
        self.assertEqual(afford_for.absd_amount, 1200000.0)

    def test_tdsr_and_msr_affordability(self):
        """Test TDSR (55%) and MSR (30%) regulatory affordability checks."""
        afford = self.env['moneta.singapore.property.affordability'].create({
            'name': 'Household Affordability Check',
            'property_price': 1000000.0,
            'gross_monthly_income': 12000.0,
            'other_monthly_debt_commitments': 1000.0,
            'loan_tenure_years': 25,
            'hdb_loan_rate': 2.60,
            'bank_sora_rate': 3.20,
            'stress_test_rate': 4.00,
        })
        self.assertEqual(afford.max_monthly_tdsr_allowance, 6600.0)  # 12000 * 55%
        self.assertEqual(afford.max_monthly_msr_allowance, 3600.0)   # 12000 * 30%
        self.assertTrue(afford.tdsr_passed)
        self.assertTrue(afford.msr_passed)
