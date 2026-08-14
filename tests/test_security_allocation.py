# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from .common import MonetaTestBase


class TestSecurityAllocation(MonetaTestBase):
    """Test asset class weighting and allocations for securities (v1.14.0)."""

    def setUp(self):
        super().setUp()
        self.security = self.env['moneta.security'].create({
            'name': 'Vanguard Balanced ETF',
            'symbol': 'VBAL',
            'asset_class': 'etf',
            'currency_id': self.currency.id,
            'website_url': 'https://vanguard.ca',
            'ir_url': 'https://investor.vanguard.ca',
        })

    def test_valid_allocation_sum(self):
        """Creating allocations summing to <= 100% succeeds and computes total weight."""
        self.env['moneta.security.allocation'].create({
            'security_id': self.security.id,
            'asset_class': 'stock',
            'weight': 60.0,
            'country_code': 'US',
        })
        self.env['moneta.security.allocation'].create({
            'security_id': self.security.id,
            'asset_class': 'bond',
            'weight': 40.0,
            'country_code': 'US',
        })

        self.security.invalidate_recordset(['total_allocation_weight'])
        self.assertAlmostEqual(self.security.total_allocation_weight, 100.0, places=2)

    def test_invalid_weight_range(self):
        """A single allocation with weight > 100% or < 0% fails validation."""
        with self.assertRaises(ValidationError):
            self.env['moneta.security.allocation'].create({
                'security_id': self.security.id,
                'asset_class': 'stock',
                'weight': 150.0,
            })

        with self.assertRaises(ValidationError):
            self.env['moneta.security.allocation'].create({
                'security_id': self.security.id,
                'asset_class': 'bond',
                'weight': -10.0,
            })

    def test_invalid_allocation_sum_exceeds_100(self):
        """Total allocation weight across a security exceeding 100% raises ValidationError."""
        self.env['moneta.security.allocation'].create({
            'security_id': self.security.id,
            'asset_class': 'stock',
            'weight': 70.0,
        })
        with self.assertRaises(ValidationError):
            self.env['moneta.security.allocation'].create({
                'security_id': self.security.id,
                'asset_class': 'bond',
                'weight': 40.0,
            })
