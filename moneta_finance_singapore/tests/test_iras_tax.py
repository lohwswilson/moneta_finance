# -*- coding: utf-8 -*-
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestIRASTaxPlanner(MonetaTestBase):

    def test_iras_tax_brackets_calculation(self):
        """Test Singapore IRAS progressive tax bracket computation for YA 2024-2026."""
        # Income $140k with $40k reliefs -> Chargeable Income = $100,000
        # Tax: First $80k = $3,350; next $20k @ 11.5% = $2,300 -> Total = $5,650
        tax_plan = self.env['moneta.iras.tax.planner'].create({
            'tax_year': 2026,
            'annual_employment_income': 120000.0,
            'annual_bonus': 20000.0,
            'cpf_employee_relief': 20400.0,
            'rstu_self_relief': 8000.0,
            'srs_contribution_relief': 7600.0,
            'nsman_relief_type': 'active_ict_ippt',  # 3000
            'charitable_donations': 0.0,
        })

        # Total assessable income = 140,000
        self.assertEqual(tax_plan.gross_total_income, 140000.0)
        # Reliefs: EIR 1000 + CPF 20400 + RSTU 8000 + SRS 7600 + NSman 3000 = 40,000
        self.assertEqual(tax_plan.total_personal_reliefs_pre_cap, 40000.0)
        self.assertEqual(tax_plan.effective_reliefs_applied, 40000.0)
        self.assertEqual(tax_plan.chargeable_income, 100000.0)

        # Tax calculation: $3,350 + ($20,000 * 0.115) = $5,650
        self.assertEqual(tax_plan.marginal_tax_bracket_pct, 11.5)
        self.assertEqual(tax_plan.gross_tax_payable, 5650.0)
        self.assertEqual(tax_plan.net_tax_payable, 5650.0)
        self.assertAlmostEqual(tax_plan.effective_tax_rate_pct, 4.04, delta=0.05)

    def test_iras_80k_relief_cap_and_donations(self):
        """Test $80,000 personal relief ceiling and 250% uncapped charitable donations."""
        tax_plan = self.env['moneta.iras.tax.planner'].create({
            'tax_year': 2026,
            'annual_employment_income': 300000.0,
            'cpf_employee_relief': 20400.0,
            'rstu_self_relief': 8000.0,
            'rstu_family_relief': 8000.0,
            'srs_contribution_relief': 15300.0,
            'qualifying_child_count': 3,          # 12,000
            'parent_relief_type': 'staying',       # 9,000
            'course_fees_relief': 5500.0,
            'life_insurance_relief': 5000.0,
            'nsman_relief_type': 'key_appointment',# 5,000
            'charitable_donations': 10000.0,       # 250% = 25,000 (uncapped)
        })

        # Pre-cap personal sum exceeds $80,000
        self.assertGreater(tax_plan.total_personal_reliefs_pre_cap, 80000.0)
        self.assertEqual(tax_plan.remaining_cap_to_80k, 0.0)
        # Effective deductions = $80,000 cap + $25,000 donation = $105,000
        self.assertEqual(tax_plan.donation_deduction_amount, 25000.0)
        self.assertEqual(tax_plan.effective_reliefs_applied, 105000.0)
        self.assertEqual(tax_plan.chargeable_income, 195000.0)

    def test_tax_optimization_advisory(self):
        """Test generation of year-end tax optimization recommendations."""
        tax_plan = self.env['moneta.iras.tax.planner'].create({
            'tax_year': 2026,
            'annual_employment_income': 150000.0,
            'cpf_employee_relief': 20400.0,
            'rstu_self_relief': 0.0,
            'srs_contribution_relief': 0.0,
            'nsman_relief_type': 'none',
        })
        self.assertGreater(tax_plan.remaining_cap_to_80k, 20000.0)
        self.assertIn('CPF RSTU (Self)', tax_plan.optimization_advisory)
        self.assertIn('SRS Contribution', tax_plan.optimization_advisory)
