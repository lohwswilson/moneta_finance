# -*- coding: utf-8 -*-
import base64
from datetime import date
from odoo.tests import tagged
from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestTaxSchedule(MonetaTestBase):

    def test_tax_schedule_aggregation_and_txf_export(self):
        """Test annual tax schedule calculation and TurboTax TXF file export."""
        year = 2025
        acc = self.env['moneta.account'].create({
            'name': 'IBKR Brokerage',
            'account_type': 'brokerage',
            'currency_id': self.env.company.currency_id.id,
            'opening_balance': 50000.0,
        })
        sec = self.env['moneta.security'].create({
            'name': 'Tesla Inc.',
            'symbol': 'TSLA',
            'current_price': 250.0,
            'currency_id': self.env.company.currency_id.id,
        })

        # 1. Buy on 2024-01-10 (Long-term when sold in 2025)
        self.env['moneta.investment.transaction'].create({
            'account_id': acc.id,
            'security_id': sec.id,
            'action': 'buy',
            'trade_date': date(2024, 1, 10),
            'quantity': 50.0,
            'price': 200.0,
        })

        # 2. Buy on 2025-01-10 (Short-term when sold in 2025-06)
        self.env['moneta.investment.transaction'].create({
            'account_id': acc.id,
            'security_id': sec.id,
            'action': 'buy',
            'trade_date': date(2025, 1, 10),
            'quantity': 50.0,
            'price': 210.0,
        })

        # 3. Sell 60 shares on 2025-06-15 (FIFO: 50 Long-Term @ $200, 10 Short-Term @ $210)
        self.env['moneta.investment.transaction'].create({
            'account_id': acc.id,
            'security_id': sec.id,
            'action': 'sell',
            'trade_date': date(2025, 6, 15),
            'quantity': 60.0,
            'price': 250.0,
            'lot_disposal_strategy': 'fifo',
        })

        # 4. Dividend on 2025-08-01 ($500)
        self.env['moneta.investment.transaction'].create({
            'account_id': acc.id,
            'security_id': sec.id,
            'action': 'dividend',
            'trade_date': date(2025, 8, 1),
            'price': 500.0,
            'quantity': 1.0,
        })

        # Run Tax Schedule Wizard
        wiz = self.env['moneta.tax.schedule.wizard'].create({
            'tax_year': '2025',
        })
        wiz.action_calculate_tax_schedule()

        # Check Long-Term Gain: 50 * (250 - 200) = $2,500
        self.assertEqual(wiz.long_term_gain, 2500.0)
        # Check Short-Term Gain: 10 * (250 - 210) = $400
        self.assertEqual(wiz.short_term_gain, 400.0)
        self.assertEqual(wiz.total_capital_gain, 2900.0)
        self.assertEqual(wiz.total_dividend_income, 500.0)

        # Export TXF
        wiz.action_export_txf()
        self.assertTrue(wiz.txf_file)
        self.assertEqual(wiz.txf_filename, 'moneta_tax_schedule_2025.txf')

        # Decode TXF
        txf_text = base64.b64decode(wiz.txf_file).decode('utf-8')
        self.assertIn('V042', txf_text)
        self.assertIn('N714', txf_text)  # Long-Term Capital Gains
        self.assertIn('N712', txf_text)  # Short-Term Capital Gains
        self.assertIn('N291', txf_text)  # Dividends
