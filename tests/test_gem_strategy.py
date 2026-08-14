# -*- coding: utf-8 -*-
from datetime import date, timedelta
from .common import MonetaTestBase


class TestGemStrategy(MonetaTestBase):
    """Test GEM Strategy dual momentum evaluation and historical signals (v1.14.0)."""

    def setUp(self):
        super().setUp()
        self.sec_us = self.env['moneta.security'].create({
            'name': 'Vanguard Total Stock Market', 'symbol': 'VTI', 'asset_class': 'etf', 'currency_id': self.currency.id,
        })
        self.sec_world = self.env['moneta.security'].create({
            'name': 'Vanguard FTSE All-World ex-US', 'symbol': 'VEU', 'asset_class': 'etf', 'currency_id': self.currency.id,
        })
        self.sec_safe = self.env['moneta.security'].create({
            'name': 'Vanguard Total Bond Market', 'symbol': 'BND', 'asset_class': 'bond', 'currency_id': self.currency.id,
        })
        self.sec_rf = self.env['moneta.security'].create({
            'name': 'SPDR 1-3 Month T-Bill', 'symbol': 'BIL', 'asset_class': 'cash', 'currency_id': self.currency.id,
        })

        self.strategy = self.env['moneta.gem.strategy'].create({
            'name': 'Test GEM Strategy',
            'cadence': 'monthly',
            'lookback_months': 12,
            'us_equity_security_id': self.sec_us.id,
            'world_equity_security_id': self.sec_world.id,
            'safe_asset_security_id': self.sec_safe.id,
            'risk_free_security_id': self.sec_rf.id,
        })

    def _seed_prices(self, security, start_price, end_price, start_date, end_date):
        self.env['moneta.security.price'].create({
            'security_id': security.id,
            'price_date': start_date,
            'price_close': start_price,
        })
        self.env['moneta.security.price'].create({
            'security_id': security.id,
            'price_date': end_date,
            'price_close': end_price,
        })

    def test_gem_risk_on_evaluation(self):
        """When US equity beats risk-free, signal evaluates to Risk-On."""
        today = date.today()
        year_ago = today - timedelta(days=365)

        # US Equities: +20%
        self._seed_prices(self.sec_us, 100.0, 120.0, year_ago, today)
        # World Equities: +10%
        self._seed_prices(self.sec_world, 50.0, 55.0, year_ago, today)
        # Safe Asset: +2%
        self._seed_prices(self.sec_safe, 80.0, 81.6, year_ago, today)
        # Risk-free: +4%
        self._seed_prices(self.sec_rf, 90.0, 93.6, year_ago, today)

        self.strategy.action_evaluate_signal()

        self.strategy.invalidate_recordset()
        self.assertEqual(self.strategy.current_signal, 'risk_on_us')
        self.assertEqual(self.strategy.target_security_id, self.sec_us)
        self.assertTrue(len(self.strategy.signal_ids) >= 1)

    def test_gem_risk_off_evaluation(self):
        """When US equity falls below risk-free, signal evaluates to Risk-Off Safe Asset."""
        today = date.today()
        year_ago = today - timedelta(days=365)

        # US Equities: -10%
        self._seed_prices(self.sec_us, 100.0, 90.0, year_ago, today)
        # World Equities: -15%
        self._seed_prices(self.sec_world, 50.0, 42.5, year_ago, today)
        # Safe Asset: +5%
        self._seed_prices(self.sec_safe, 80.0, 84.0, year_ago, today)
        # Risk-free: +4%
        self._seed_prices(self.sec_rf, 90.0, 93.6, year_ago, today)

        self.strategy.action_evaluate_signal()

        self.strategy.invalidate_recordset()
        self.assertEqual(self.strategy.current_signal, 'risk_off_safe')
        self.assertEqual(self.strategy.target_security_id, self.sec_safe)
