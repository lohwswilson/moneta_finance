# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestBenchmarkComparison(MonetaTestBase):
    """Benchmark alpha must compare the portfolio and the benchmark over the
    SAME window, and must never substitute a fabricated 12.4% baseline. A
    dedicated owner isolates the seeded data from any demo records so the
    exact-value assertions are stable."""

    def setUp(self):
        super().setUp()
        self.user = self._make_user('Bench User', 'bench@example.com')
        self.account = self._make_account(
            user=self.user, name='Bench Brokerage',
            account_type='brokerage', opening_balance=0.0)
        self.sec_hold = self.env['moneta.security'].create({
            'name': 'Hold Co', 'symbol': 'HOLD', 'asset_class': 'stock',
        })
        self.sec_bench = self.env['moneta.security'].create({
            'name': 'S&P 500 ETF', 'symbol': 'VOO',
            'asset_class': 'etf', 'is_benchmark': True,
        })

    def _buy(self, days_ago, price):
        return self.env['moneta.investment.transaction'].create({
            'action': 'buy', 'account_id': self.account.id,
            'security_id': self.sec_hold.id,
            'quantity': 10.0, 'price': price,
            'trade_date': date.today() - timedelta(days=days_ago),
        })

    def _price(self, security, days_ago, close):
        return self.env['moneta.security.price'].create({
            'security_id': security.id,
            'price_date': date.today() - timedelta(days=days_ago),
            'price_close': close,
        })

    def _bench(self, period='1y', with_benchmark=True):
        return self.env['moneta.benchmark.comparison'].create({
            'name': 'Test Bench', 'period': period, 'user_id': self.user.id,
            'benchmark_security_id': self.sec_bench.id if with_benchmark else False,
        })

    def test_alpha_same_window_no_fabrication(self):
        # Portfolio: buy 10 @ 100 well before the window; 100 at start, 120 today (+20%).
        self._buy(400, 100.0)
        self._price(self.sec_hold, 365, 100.0)
        self._price(self.sec_hold, 0, 120.0)
        # Benchmark: 100 at start, 110 today (+10%).
        self._price(self.sec_bench, 365, 100.0)
        self._price(self.sec_bench, 0, 110.0)
        bench = self._bench()
        bench._compute_returns()
        self.assertAlmostEqual(round(bench.portfolio_return_pct, 2), 20.0, places=1)
        self.assertAlmostEqual(round(bench.benchmark_return_pct, 2), 10.0, places=1)
        # Same window -> alpha is the difference (not a since-inception mismatch).
        self.assertAlmostEqual(round(bench.alpha_pct, 2), 10.0, places=1)

    def test_no_benchmark_prices_means_zero_not_fabricated(self):
        # Portfolio valued over the window; NO benchmark price history at all.
        self._buy(400, 100.0)
        self._price(self.sec_hold, 365, 100.0)
        self._price(self.sec_hold, 0, 120.0)
        bench = self._bench()
        bench._compute_returns()
        self.assertAlmostEqual(round(bench.portfolio_return_pct, 2), 20.0, places=1)
        # No fabricated 12.4% baseline -- the benchmark return is 0.0 (unknown).
        self.assertEqual(round(bench.benchmark_return_pct, 2), 0.0)
        # Windows do not match -> alpha suppressed, not a made-up figure.
        self.assertEqual(round(bench.alpha_pct, 2), 0.0)

    def test_alpha_suppressed_when_portfolio_window_unvaluable(self):
        # Portfolio buy before the window but ONLY a price today (none at start)
        # -> the window start cannot be valued.
        self._buy(400, 100.0)
        self._price(self.sec_hold, 0, 120.0)
        # Benchmark priced over the window (+10%).
        self._price(self.sec_bench, 365, 100.0)
        self._price(self.sec_bench, 0, 110.0)
        bench = self._bench()
        bench._compute_returns()
        self.assertEqual(round(bench.portfolio_return_pct, 2), 0.0)  # window unvaluable
        self.assertAlmostEqual(round(bench.benchmark_return_pct, 2), 10.0, places=1)
        # Benchmark alone must not fabricate an alpha against an unknown portfolio.
        self.assertEqual(round(bench.alpha_pct, 2), 0.0)

    def test_contributions_in_window_are_subtracted(self):
        # A buy INSIDE the window adds capital that must be subtracted from the
        # gain so the return reflects price movement, not new money.
        self._buy(400, 100.0)                      # 10 @ 100 before the window
        self._price(self.sec_hold, 365, 100.0)     # start: 10 * 100 = 1000
        # Buy 5 more @ 120 inside the window (contribution +600).
        self.env['moneta.investment.transaction'].create({
            'action': 'buy', 'account_id': self.account.id,
            'security_id': self.sec_hold.id,
            'quantity': 5.0, 'price': 120.0,
            'trade_date': date.today() - timedelta(days=180),
        })
        self._price(self.sec_hold, 0, 120.0)       # end: 15 * 120 = 1800
        self._price(self.sec_bench, 365, 100.0)
        self._price(self.sec_bench, 0, 110.0)
        bench = self._bench()
        bench._compute_returns()
        # (1800 - 1000 - 600) / 1000 = 20% -- the in-window buy is netted out.
        self.assertAlmostEqual(round(bench.portfolio_return_pct, 2), 20.0, places=1)
        self.assertAlmostEqual(round(bench.benchmark_return_pct, 2), 10.0, places=1)
        self.assertAlmostEqual(round(bench.alpha_pct, 2), 10.0, places=1)