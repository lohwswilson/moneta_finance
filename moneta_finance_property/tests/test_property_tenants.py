# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestPropertyTenants(MonetaTestBase):

    def test_tenant_lease_and_rent_roll(self):
        """Test landlord tenant lease management, rent schedule generation, and property NOI / yield."""
        prop = self.env['moneta.property'].create({
            'name': 'Marina Bay Luxury Condo #18-02',
            'asset_category': 'real_estate',
            'property_type': 'rental_property',
            'current_market_value': 1200000.0,
            'monthly_property_tax': 300.0,
            'monthly_insurance': 100.0,
            'monthly_hoa_maintenance': 200.0,
        })

        start_d = date(2025, 1, 1)
        end_d = date(2025, 12, 31)

        tenant = self.env['moneta.property.tenant'].create({
            'name': 'John Doe',
            'property_id': prop.id,
            'unit_number': '#18-02',
            'lease_start_date': start_d,
            'lease_end_date': end_d,
            'monthly_rent_amount': 4000.0,
            'rent_due_day': 1,
            'security_deposit_held': 8000.0,
        })

        # Generate 12 months rent schedule
        tenant.action_generate_rent_schedule()
        self.assertEqual(len(tenant.rent_payment_ids), 12)

        # Check property rental metrics
        self.assertEqual(prop.tenant_count, 1)
        self.assertEqual(prop.gross_annual_rental_income, 48000.0)
        self.assertEqual(prop.gross_rental_yield_pct, 4.0)
        self.assertEqual(prop.net_operating_income, 40800.0)
        self.assertEqual(prop.occupancy_rate_pct, 100.0)

        # Mark 3 payments as paid
        p1 = tenant.rent_payment_ids.filtered(lambda p: p.period_month == date(2025, 1, 1))
        p2 = tenant.rent_payment_ids.filtered(lambda p: p.period_month == date(2025, 2, 1))
        p3 = tenant.rent_payment_ids.filtered(lambda p: p.period_month == date(2025, 3, 1))

        p1.action_mark_paid()
        p2.action_mark_paid()
        p3.action_mark_paid()

        self.assertEqual(p1.payment_status, 'paid')
        self.assertEqual(tenant.total_rent_collected, 12000.0)

    def test_property_home_equity(self):
        """Test real estate asset creation, mortgage linkage, and dynamic equity calculation."""
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

        # Make a mortgage payment of $50,000 to reduce debt
        self.env['moneta.transaction'].create({
            'account_id': mortgage.id,
            'amount': 50000.0,
            'state': 'cleared',
        })
        self.assertEqual(mortgage.current_balance, -350000.0)
        # Property equity should dynamically update to $250,000
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
