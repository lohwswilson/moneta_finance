# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestInvestment(MonetaTestBase):

    def _brokerage(self):
        return self._make_account(name='Brokerage', account_type='brokerage', opening_balance=0.0)

    def _security(self, symbol='AAPL'):
        return self.env['moneta.security'].create({'name': '%s Inc' % symbol, 'symbol': symbol})

    def _inv_tx(self, account, security, action, qty, price=None, commission=0.0, **kw):
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
        vals.update(kw)
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

    def test_sell_unknown_price_sets_realized_gain_null(self):
        # A sell with a NULL price has unknowable proceeds, so the realized
        # gain is NULL (null propagation), never 0.0 -- the ORM coerces
        # False/None to 0.0, so the column is asserted directly.
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0)
        sell = self._inv_tx(acc, sec, 'sell', 5.0)  # price NULL
        self.assertTrue(self._is_null(self.env['moneta.investment.transaction'], sell.id, 'realized_gain'))

    def test_dividend_unknown_amount_sets_realized_gain_null(self):
        # A dividend with a NULL price has an unknowable amount, so its
        # realized gain is NULL too (no cash entry is posted either).
        acc = self._brokerage()
        sec = self._security()
        div = self._inv_tx(acc, sec, 'dividend', 1.0)  # price NULL
        self.assertTrue(self._is_null(self.env['moneta.investment.transaction'], div.id, 'realized_gain'))

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

    # ------------------------------------------------------------------
    # TWR (Modified Dietz) & MWR (XIRR) -- regression tests for the real
    # return algorithms that replaced the unrealized-gain-percent stub.
    # ------------------------------------------------------------------

    def _price(self, security, days_ago, close):
        """Seed a daily price entry ``days_ago`` days before today."""
        d = fields.Date.context_today(self.env.user) - timedelta(days=days_ago)
        return self.env['moneta.security.price'].create({
            'security_id': security.id, 'price_date': d, 'price_close': close,
        })

    def test_returns_single_buy_held_one_year(self):
        # Buy 10 @ 100 exactly one year ago; price today is 120 (+20%).
        acc = self._brokerage()
        sec = self._security()
        today = fields.Date.context_today(self.env.user)
        d0 = today - timedelta(days=365)
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0, trade_date=d0)
        self._price(sec, 0, 120.0)
        h = self._holding(acc, sec)
        h.invalidate_recordset()
        # MWR (XIRR) annualizes the +20% total return over exactly one year.
        self.assertAlmostEqual(round(h.mwr_percent, 2), 20.0, places=1)
        # TWR (Modified Dietz) is the period return over the same window.
        self.assertAlmostEqual(round(h.twr_percent, 2), 20.0, places=1)

    def test_returns_fully_sold_one_year(self):
        # Buy 10 @ 100 one year ago, sell 10 @ 120 today: realized +20%/yr.
        acc = self._brokerage()
        sec = self._security()
        today = fields.Date.context_today(self.env.user)
        d0 = today - timedelta(days=365)
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0, trade_date=d0)
        self._inv_tx(acc, sec, 'sell', 10.0, 120.0, trade_date=today)
        h = self._holding(acc, sec)
        h.invalidate_recordset()
        self.assertAlmostEqual(round(h.mwr_percent, 2), 20.0, places=1)
        self.assertAlmostEqual(round(h.twr_percent, 2), 20.0, places=1)

    def test_returns_fallback_unknown_basis(self):
        # Buy with no price -> unknown cost basis -> returns fall back to the
        # unrealized-gain percent (0.0 while the basis is unknown).
        acc = self._brokerage()
        sec = self._security()
        self._inv_tx(acc, sec, 'buy', 10.0)  # price unset: cost unknown
        self._price(sec, 0, 120.0)
        h = self._holding(acc, sec)
        h.invalidate_recordset()
        self.assertEqual(round(h.mwr_percent, 4), 0.0)
        self.assertEqual(round(h.twr_percent, 4), 0.0)

    def test_returns_fallback_unknown_sell_price(self):
        # A sell with a NULL price has unknowable proceeds -> cannot compute a
        # money-weighted return; falls back to the unrealized-gain percent.
        acc = self._brokerage()
        sec = self._security()
        today = fields.Date.context_today(self.env.user)
        d0 = today - timedelta(days=365)
        self._inv_tx(acc, sec, 'buy', 10.0, 100.0, trade_date=d0)
        self._inv_tx(acc, sec, 'sell', 5.0, trade_date=today)  # price NULL
        self._price(sec, 0, 120.0)
        h = self._holding(acc, sec)
        h.invalidate_recordset()
        # 5 shares remain @ avg 100, priced 120 -> +20% unrealized -> fallback.
        self.assertAlmostEqual(round(h.mwr_percent, 2), 20.0, places=1)
        self.assertAlmostEqual(round(h.twr_percent, 2), 20.0, places=1)

    def test_returns_compute_on_multi_record_batch(self):
        # Regression: the dashboard list view reads TWR / MWR for all holdings
        # at once, so the compute runs on the whole prefetch set. Touching the
        # valuation fields via attribute access on that set raised
        # "ValueError: Expected singleton: moneta.holding(1, 2, 3)".
        acc = self._brokerage()
        sec1 = self._security('AAPL')
        sec2 = self._security('MSFT')
        sec3 = self._security('GOOG')
        today = fields.Date.context_today(self.env.user)
        d0 = today - timedelta(days=365)
        self._inv_tx(acc, sec1, 'buy', 10.0, 100.0, trade_date=d0)
        self._inv_tx(acc, sec2, 'buy', 5.0, 200.0, trade_date=d0)
        self._inv_tx(acc, sec3, 'buy', 2.0, 500.0, trade_date=d0)
        self._price(sec1, 0, 120.0)
        self._price(sec2, 0, 220.0)
        self._price(sec3, 0, 550.0)
        holdings = self.env['moneta.holding'].search([('account_id', '=', acc.id)])
        self.assertEqual(len(holdings), 3)
        holdings.invalidate_recordset()
        # read() on the whole set is the list-view path: the first record's
        # cache miss computes the field on the entire prefetch set at once.
        # Expected returns: AAPL 10@100 -> 120 (+20%), MSFT 5@200 -> 220 (+10%),
        # GOOG 2@500 -> 550 (+10%).
        by_sec = {h.security_id.id: h.id for h in holdings}
        expected = {by_sec[sec1.id]: 20.0, by_sec[sec2.id]: 10.0, by_sec[sec3.id]: 10.0}
        vals = holdings.read(['twr_percent', 'mwr_percent'])
        self.assertEqual(len(vals), 3)
        for v in vals:
            self.assertAlmostEqual(round(v['twr_percent'], 2), expected[v['id']], places=1)
            self.assertAlmostEqual(round(v['mwr_percent'], 2), expected[v['id']], places=1)