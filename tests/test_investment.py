# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestInvestment(MonetaTestBase):

    def _brokerage(self):
        return self._make_account(name='Brokerage', account_type='brokerage', opening_balance=0.0)

    def _security(self, symbol='AAPL'):
        return self.env['moneta.security'].create({'name': '%s Inc' % symbol, 'symbol': symbol})

    def _inv_tx(self, account, security, action, qty, price=None, commission=0.0):
        vals = {
            'action': action,
            'account_id': account.id,
            'security_id': security.id,
            'quantity': qty,
        }
        if price is not None:
            vals['price'] = price
        if commission:
            vals['commission'] = commission
        return self.env['moneta.investment.transaction'].create(vals)

    def _holding(self, account, security):
        return self.env['moneta.holding'].search([
            ('account_id', '=', account.id),
            ('security_id', '=', security.id),
        ], limit=1)

    def _is_null(self, model, rec_id, fname):
        # Odoo reads NULL numerics as 0.0, so null propagation is asserted at
        # the column level.
        self.env.cr.execute(
            "SELECT %s IS NULL FROM %s WHERE id = %%s" % (fname, model._table),
            (rec_id,),
        )
        return self.env.cr.fetchone()[0]

    def test_buy_creates_holding_with_commission_in_basis(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0, commission=10.0)
        h = self._holding(acc, sec)
        self.assertTrue(h)
        self.assertEqual(round(h.quantity, 4), 10.0)
        self.assertEqual(round(h.average_cost or 0.0, 4), 101.0)  # (10*100 + 10) / 10

    def test_second_buy_blends_average(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0, commission=10.0)
        self._inv_tx(acc, sec, 'buy', 10.0, 120.0, commission=20.0)
        h = self._holding(acc, sec)
        self.assertEqual(round(h.quantity, 4), 20.0)
        self.assertEqual(round(h.average_cost or 0.0, 4), 111.5)  # (1010 + 1200 + 20) / 20

    def test_sell_relieves_quantity_and_sets_realized_gain(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 20.0, 100.0)
        sell = self._inv_tx(acc, sec, 'sell', 5.0, 150.0, commission=10.0)
        h = self._holding(acc, sec)
        self.assertEqual(round(h.quantity, 4), 15.0)
        self.assertEqual(round(h.average_cost or 0.0, 4), 100.0)  # unchanged by sells
        self.assertEqual(round(sell.realized_gain or 0.0, 4), 240.0)  # (5*150 - 10) - 5*100

    def test_sell_exceeding_holding_rejected(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0)
        with self.assertRaises(ValidationError):
            self._inv_tx(acc, sec, 'sell', 11.0, 100.0)
        # Rejection before write: only the buy exists.
        self.assertEqual(self.env['moneta.investment.transaction'].search_count([]), 1)

    def test_split_scales_quantity_and_average(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0)  # avg 100
        self._inv_tx(acc, sec, 'split', 2.0)  # 2:1 split
        h = self._holding(acc, sec)
        self.assertEqual(round(h.quantity, 4), 20.0)
        self.assertEqual(round(h.average_cost or 0.0, 4), 50.0)

    def test_dividend_creates_cash_income_and_realized_gain(self):
        acc = self._brokerage()
        sec = self._security()
        div = self._inv_tx(acc, sec, 'dividend', 1.0, 100.0)
        self.assertEqual(round(div.realized_gain or 0.0, 4), 100.0)
        cash = div.linked_transaction_id
        self.assertTrue(cash)
        self.assertEqual(cash.account_id, acc)
        self.assertEqual(round(cash.amount, 4), 100.0)
        # The brokerage cash balance moved via the linked transaction.
        self.assertEqual(self._current_balance(acc), 100.0)

    def test_unknown_price_buy_keeps_average_null(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 5.0)  # price unset: cost unknown
        h = self._holding(acc, sec)
        self.assertEqual(round(h.quantity, 4), 5.0)
        self.assertTrue(self._is_null(self.env['moneta.holding'], h.id, 'average_cost'))
        # A later known-price buy cannot blend into the unknown basis
        # (null propagation: an unknown component keeps the total unknown).
        self._inv_tx(acc, sec, 'buy', 5.0, 50.0)
        h.invalidate_recordset()
        self.assertTrue(self._is_null(self.env['moneta.holding'], h.id, 'average_cost'))

    def test_market_value_null_without_price(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0)
        h = self._holding(acc, sec)
        # No price entry yet: price_known False marks the valuation unknown
        # (the numeric field itself reads 0.0 -- Odoo coercion).
        h.invalidate_recordset()
        self.assertTrue(h.price_known is False)
        self.env['moneta.security.price'].create({
            'security_id': sec.id, 'price_date': '2026-08-01', 'price_close': 120.0,
        })
        h.invalidate_recordset()
        self.assertTrue(h.price_known)
        self.assertEqual(round(h.market_value or 0.0, 4), 1200.0)
        self.assertEqual(round(h.unrealized_gain or 0.0, 4), 200.0)

    def test_unrealized_gain_null_when_basis_unknown(self):
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0)  # unknown cost
        self.env['moneta.security.price'].create({
            'security_id': sec.id, 'price_date': '2026-08-01', 'price_close': 120.0,
        })
        h = self._holding(acc, sec)
        h.invalidate_recordset()
        # Market value is known (price exists); the gain needs the basis too:
        # basis_known False marks the unrealized gain unknown.
        self.assertTrue(h.price_known)
        self.assertTrue(h.basis_known is False)
        self.assertEqual(round(h.market_value or 0.0, 4), 1200.0)
        self.assertEqual(round(h.unrealized_gain or 0.0, 4), 0.0)

    def test_holding_removed_when_last_transaction_deleted(self):
        acc = self._brokerage()
        sec = self._security()
        tx = self._inv_tx(acc, sec, 'buy', 10.0, 100.0)
        self.assertTrue(self._holding(acc, sec))
        tx.unlink()
        self.assertFalse(self._holding(acc, sec))