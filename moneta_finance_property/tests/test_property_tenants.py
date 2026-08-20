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
