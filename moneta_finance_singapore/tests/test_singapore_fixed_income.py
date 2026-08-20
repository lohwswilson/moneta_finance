# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestSingaporeFixedIncome(MonetaTestBase):

    def test_ssb_bond_step_up_yield_and_validation(self):
        """Test Singapore Savings Bonds (SSB) 10-year step-up schedule and constraints."""
        ssb = self.env['moneta.ssb.bond'].create({
            'issue_code': 'SBJAN26 GX26010T',
            'investment_amount': 20000.0,
            'funding_source': 'cash',
            'rate_year_1': 2.80,
            'rate_year_2': 2.85,
            'rate_year_3': 2.90,
            'rate_year_4': 2.95,
            'rate_year_5': 3.00,
            'rate_year_6': 3.05,
            'rate_year_7': 3.10,
            'rate_year_8': 3.15,
            'rate_year_9': 3.20,
            'rate_year_10': 3.30,
        })
        self.assertEqual(ssb.average_10yr_yield, 3.03)
        self.assertAlmostEqual(ssb.total_interest_to_maturity, 6060.0, delta=10.0)
        self.assertEqual(ssb.next_coupon_payout, 280.0)  # 20000 * 2.8% / 2

        # Test invalid $500 multiple
        with self.assertRaises(ValidationError):
            self.env['moneta.ssb.bond'].create({
                'issue_code': 'INVALID',
                'investment_amount': 1234.0,
            })

        # Test exceeding $200k cap
        with self.assertRaises(ValidationError):
            self.env['moneta.ssb.bond'].create({
                'issue_code': 'TOO_HIGH',
                'investment_amount': 250000.0,
            })

    def test_tbill_discount_and_annualized_yield(self):
        """Test MAS Treasury Bill discount auction yield accounting."""
        tbill = self.env['moneta.tbill'].create({
            'issue_code': 'BS26105A',
            'tenure_type': '6_month',
            'face_value': 10000.0,
            'issue_price_per_hundred': 98.15,
            'funding_source': 'cpf_oa',
        })
        self.assertEqual(tbill.total_investment_cost, 9815.0)
        self.assertEqual(tbill.net_discount_profit, 185.0)
        # Yield = (185 / 9815) * (365 / 182) * 100 = ~3.78%
        self.assertAlmostEqual(tbill.cut_off_yield_p_a, 3.78, delta=0.05)

    def test_sgx_security_and_ucits_etf_detection(self):
        """Test automatic detection of SGX tax-exempt stocks and Irish UCITS ETFs."""
        # 1. SGX DBS Group Holdings
        dbs = self.env['moneta.security'].create({
            'name': 'DBS Group Holdings Ltd',
            'symbol': 'D05.SI',
            'exchange': 'SGX',
        })
        self.assertTrue(dbs.is_sgx_security)
        self.assertEqual(dbs.dividend_tax_treatment, 'sg_tax_exempt')

        # 2. Irish UCITS S&P 500 ETF (London Stock Exchange)
        cspx = self.env['moneta.security'].create({
            'name': 'iShares Core S&P 500 UCITS ETF',
            'symbol': 'CSPX.L',
            'exchange': 'LSE',
        })
        self.assertTrue(cspx.is_ucits_etf)
        self.assertEqual(cspx.dividend_tax_treatment, 'ucits_wht_15')

        # 3. US Vanguard S&P 500 ETF
        voo = self.env['moneta.security'].create({
            'name': 'Vanguard S&P 500 ETF',
            'symbol': 'VOO',
            'exchange': 'NYSE Arca',
        })
        self.assertFalse(voo.is_sgx_security)
        self.assertFalse(voo.is_ucits_etf)
        self.assertEqual(voo.dividend_tax_treatment, 'us_wht_30')

    def test_ucits_vs_us_etf_tax_comparator(self):
        """Test UCITS 15% vs 30% dividend withholding tax and US estate tax savings."""
        comp = self.env['moneta.ucits.etf.comparator'].create({
            'name': 'S&P 500 Comparison',
            'portfolio_value': 200000.0,
            'dividend_yield_pct': 1.50,
            'investment_horizon_years': 20,
        })
        # Gross dividends = $200k * 1.5% = $3,000
        self.assertEqual(comp.annual_dividend_gross, 3000.0)
        # US drag (30%) = $900, UCITS drag (15%) = $450
        self.assertEqual(comp.us_etf_annual_tax_drag, 900.0)
        self.assertEqual(comp.ucits_annual_tax_drag, 450.0)
        self.assertEqual(comp.annual_tax_savings_with_ucits, 450.0)
        self.assertGreater(comp.cumulative_tax_savings_horizon, 15000.0)
        # US estate tax exposure on $200k - $60k = $140k @ 40% = $56,000
        self.assertEqual(comp.us_estate_tax_exposure, 56000.0)
        self.assertEqual(comp.ucits_estate_tax_exposure, 0.0)
