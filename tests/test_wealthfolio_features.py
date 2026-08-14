# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date


class TestWealthfolioFeatures(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.account = self.env['moneta.account'].create({
            'name': 'Robinhood Brokerage',
            'account_type': 'brokerage',
            'opening_balance': 10000.0,
        })
        self.sec_aapl = self.env['moneta.security'].create({
            'name': 'Apple Inc.',
            'symbol': 'AAPL',
            'asset_class': 'stock',
            'annual_dividend_rate': 1.00,
            'dividend_yield_pct': 0.45,
        })
        self.sec_voo = self.env['moneta.security'].create({
            'name': 'Vanguard S&P 500 ETF',
            'symbol': 'VOO',
            'asset_class': 'etf',
            'is_benchmark': True,
            'annual_dividend_rate': 6.50,
            'dividend_yield_pct': 1.45,
        })

    def test_target_allocation_and_rebalancer(self):
        """Test target asset allocation drift and rebalancing advisor."""
        # Buy 50 shares of AAPL at 150
        self.env['moneta.investment.transaction'].create({
            'action': 'buy',
            'account_id': self.account.id,
            'security_id': self.sec_aapl.id,
            'quantity': 50.0,
            'price': 150.0,
            'trade_date': date(2026, 8, 1),
        })

        # Set target allocation: 80% stock, 20% cash
        target_stock = self.env['moneta.target.allocation'].create({
            'asset_class': 'stock',
            'target_weight': 80.0,
        })
        target_stock._compute_actual_allocation()
        self.assertTrue(target_stock.actual_weight > 0)

        # Run rebalance wizard
        wiz = self.env['moneta.portfolio.rebalance.wizard'].create({})
        self.assertTrue(len(wiz.line_ids) > 0)

    def test_dividend_yield_and_income(self):
        """Test annual dividend calculations on holdings."""
        self.env['moneta.investment.transaction'].create({
            'action': 'buy',
            'account_id': self.account.id,
            'security_id': self.sec_aapl.id,
            'quantity': 100.0,
            'price': 200.0,
            'trade_date': date(2026, 8, 1),
        })
        holding = self.env['moneta.holding'].search([
            ('account_id', '=', self.account.id),
            ('security_id', '=', self.sec_aapl.id),
        ])
        # 100 shares * $1.00 dividend = $100.00 annual dividends
        self.assertEqual(holding.annual_dividend_income, 100.0)

    def test_stock_split_corporate_action(self):
        """Test 2-for-1 forward stock split adjusting shares and basis."""
        self.env['moneta.investment.transaction'].create({
            'action': 'buy',
            'account_id': self.account.id,
            'security_id': self.sec_aapl.id,
            'quantity': 10.0,
            'price': 200.0,
            'trade_date': date(2026, 8, 1),
        })
        holding = self.env['moneta.holding'].search([
            ('account_id', '=', self.account.id),
            ('security_id', '=', self.sec_aapl.id),
        ])
        self.assertEqual(holding.quantity, 10.0)
        self.assertEqual(holding.average_cost, 200.0)

        # Execute 2-for-1 split
        wiz = self.env['moneta.stock.split.wizard'].create({
            'security_id': self.sec_aapl.id,
            'split_ratio_type': '2_for_1',
            'split_date': date(2026, 8, 5),
        })
        wiz.action_apply_split()

        holding.invalidate_recordset()
        # After 2:1 split: 20 shares @ $100.00 average cost ($2000 total basis preserved)
        self.assertEqual(holding.quantity, 20.0)
        self.assertEqual(holding.average_cost, 100.0)

    def test_benchmark_comparison_alpha(self):
        """Test benchmark alpha return calculation."""
        bench = self.env['moneta.benchmark.comparison'].create({
            'name': '1-Year S&P 500 Alpha',
            'benchmark_security_id': self.sec_voo.id,
            'period': '1y',
        })
        bench._compute_returns()
        self.assertTrue(isinstance(bench.alpha_pct, float))
