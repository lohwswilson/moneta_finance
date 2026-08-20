# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestTaxLotAccounting(MonetaTestBase):

    def setUp(self):
        super().setUp()
        self.brokerage_acc = self.env['moneta.account'].create({
            'name': 'Interactive Brokers',
            'account_type': 'brokerage',
            'currency_id': self.env.company.currency_id.id,
            'opening_balance': 50000.0,
        })
        self.apple = self.env['moneta.security'].create({
            'name': 'Apple Inc.',
            'symbol': 'AAPL',
            'current_price': 200.0,
            'currency_id': self.env.company.currency_id.id,
        })

    def test_tax_lot_creation_on_buy(self):
        """Test that buying shares automatically creates a tax lot."""
        trade_date = date.today() - timedelta(days=400)
        buy_tx = self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'buy',
            'trade_date': trade_date,
            'quantity': 100.0,
            'price': 150.0,
            'commission': 5.0,
        })

        lots = self.env['moneta.security.lot'].search([
            ('account_id', '=', self.brokerage_acc.id),
            ('security_id', '=', self.apple.id),
        ])
        self.assertEqual(len(lots), 1)
        lot = lots[0]
        self.assertEqual(lot.initial_quantity, 100.0)
        self.assertEqual(lot.remaining_quantity, 100.0)
        self.assertEqual(lot.purchase_price, 150.0)
        self.assertEqual(lot.total_cost_basis, 15000.0)
        self.assertEqual(lot.term_type, 'long_term')
        self.assertEqual(lot.state, 'open')

    def test_tax_lot_fifo_disposal(self):
        """Test FIFO matching and disposal across multiple lots."""
        d1 = date.today() - timedelta(days=400)
        d2 = date.today() - timedelta(days=100)

        # Lot 1: 50 shs @ $100 (Long-Term)
        self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'buy',
            'trade_date': d1,
            'quantity': 50.0,
            'price': 100.0,
        })

        # Lot 2: 50 shs @ $120 (Short-Term)
        self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'buy',
            'trade_date': d2,
            'quantity': 50.0,
            'price': 120.0,
        })

        # Sell 60 shares @ $150 using FIFO
        sell_tx = self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'sell',
            'trade_date': date.today(),
            'quantity': 60.0,
            'price': 150.0,
            'lot_disposal_strategy': 'fifo',
        })

        lots = self.env['moneta.security.lot'].search([
            ('account_id', '=', self.brokerage_acc.id),
            ('security_id', '=', self.apple.id),
        ], order='purchase_date asc')

        self.assertEqual(len(lots), 2)
        lot1, lot2 = lots[0], lots[1]

        # Lot 1 should be fully sold (0 remaining)
        self.assertEqual(lot1.remaining_quantity, 0.0)
        self.assertEqual(lot1.state, 'closed')

        # Lot 2 should have 40 shares remaining
        self.assertEqual(lot2.remaining_quantity, 40.0)
        self.assertEqual(lot2.state, 'open')

        # Check sell trade's capital gains breakdown
        self.assertEqual(len(sell_tx.lot_disposal_ids), 2)
        # Lot 1 gain: 50 * (150 - 100) = $2,500 (Long-Term)
        # Lot 2 gain: 10 * (150 - 120) = $300 (Short-Term)
        self.assertEqual(sell_tx.long_term_realized_gain, 2500.0)
        self.assertEqual(sell_tx.short_term_realized_gain, 300.0)

    def test_tax_lot_hifo_disposal(self):
        """Test HIFO (Highest In, First Out) to maximize tax-loss harvesting."""
        d1 = date.today() - timedelta(days=200)
        d2 = date.today() - timedelta(days=100)

        # Lot 1: 50 shs @ $100
        self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'buy',
            'trade_date': d1,
            'quantity': 50.0,
            'price': 100.0,
        })

        # Lot 2: 50 shs @ $180 (High Cost Lot)
        self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'buy',
            'trade_date': d2,
            'quantity': 50.0,
            'price': 180.0,
        })

        # Sell 30 shares @ $140 using HIFO
        sell_tx = self.env['moneta.investment.transaction'].create({
            'account_id': self.brokerage_acc.id,
            'security_id': self.apple.id,
            'action': 'sell',
            'trade_date': date.today(),
            'quantity': 30.0,
            'price': 140.0,
            'lot_disposal_strategy': 'hifo',
        })

        lots = self.env['moneta.security.lot'].search([
            ('account_id', '=', self.brokerage_acc.id),
            ('security_id', '=', self.apple.id),
        ])
        lot_100 = lots.filtered(lambda l: l.purchase_price == 100.0)
        lot_180 = lots.filtered(lambda l: l.purchase_price == 180.0)

        # HIFO should take 30 shares from lot_180 first
        self.assertEqual(lot_180.remaining_quantity, 20.0)
        self.assertEqual(lot_100.remaining_quantity, 50.0)

        # Realized loss: 30 * (140 - 180) = -$1,200
        self.assertEqual(sell_tx.short_term_realized_gain, -1200.0)
