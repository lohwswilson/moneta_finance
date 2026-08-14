# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestBudget(MonetaTestBase):

    def _make_budget(self, category, amount, is_income=False, rollover='none'):
        budget = self.env['moneta.budget'].create({'name': 'Test Budget'})
        self.env['moneta.budget.category'].create({
            'budget_id': budget.id,
            'category_id': category.id,
            'amount': amount,
            'is_income': is_income,
            'rollover_type': rollover,
        })
        period = self.env['moneta.budget.period'].search([
            ('budget_id', '=', budget.id), ('status', '=', 'open'),
        ], limit=1)
        return budget, period

    def _line(self, period):
        return period.period_category_ids[0]

    def _spend(self, category, amount, date=None):
        acc = self._make_account(opening_balance=0.0)
        return self._make_transaction(
            acc, amount, category_id=category.id,
            transaction_date=date or fields.Date.context_today(self.env.user),
        )

    def test_create_makes_current_month_open_period(self):
        budget, period = self._make_budget(self.cat_expense, 100.0)
        today = fields.Date.context_today(self.env.user)
        self.assertEqual(period.status, 'open')
        self.assertEqual(period.period_start, today.replace(day=1))
        self.assertEqual(period.total_budgeted, 100.0)
        # The line mirrors the budget category.
        self.assertEqual(self._line(period).budgeted_amount, 100.0)
        self.assertEqual(self._line(period).effective_budget, 100.0)

    def test_actual_amount_sums_spending(self):
        _, period = self._make_budget(self.cat_expense, 100.0)
        self._spend(self.cat_expense, -40.0)
        self.assertEqual(self._line(period).actual_amount, 40.0)

    def test_actual_clamps_refunds_to_zero(self):
        _, period = self._make_budget(self.cat_expense, 100.0)
        self._spend(self.cat_expense, -100.0)
        self._spend(self.cat_expense, 30.0)  # refund
        self.assertEqual(self._line(period).actual_amount, 70.0)
        # Refunds exceeding spending clamp to 0 (never negative).
        self._spend(self.cat_expense, 90.0)
        self.assertEqual(self._line(period).actual_amount, 0.0)

    def test_income_actual_keeps_positive(self):
        _, period = self._make_budget(self.cat_income, 500.0, is_income=True)
        self._spend(self.cat_income, 500.0)
        self.assertEqual(self._line(period).actual_amount, 500.0)
        # Deductions reduce the raw sum but the income actual stays >= 0.
        self._spend(self.cat_income, -200.0)
        self.assertEqual(self._line(period).actual_amount, 300.0)

    def test_split_lines_count_once_not_double(self):
        _, period = self._make_budget(self.cat_expense, 100.0)
        acc = self._make_account(opening_balance=0.0)
        self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'amount': -100.0,
            'is_split': True,
            'state': 'cleared',
            'split_ids': [
                (0, 0, {'category_id': self.cat_expense.id, 'amount': -60.0}),
                (0, 0, {'category_id': self.cat_expense.id, 'amount': -40.0}),
            ],
        })
        # The parent has no category (nulled), so only the splits count.
        self.assertEqual(self._line(period).actual_amount, 100.0)

    def test_void_transactions_excluded(self):
        _, period = self._make_budget(self.cat_expense, 100.0)
        tx = self._spend(self.cat_expense, -50.0)
        self.assertEqual(self._line(period).actual_amount, 50.0)
        tx.write({'state': 'void'})
        self.assertEqual(self._line(period).actual_amount, 0.0)

    def test_close_rolls_over_unused_to_next_period(self):
        budget, period = self._make_budget(self.cat_expense, 100.0, rollover='monthly')
        self._spend(self.cat_expense, -60.0)
        line = self._line(period)
        self.assertEqual(line.rollover_out, 0.0)  # not closed yet
        period._close_period()
        self.assertEqual(period.status, 'closed')
        self.assertEqual(line.rollover_out, 40.0)
        next_period = self.env['moneta.budget.period'].search([
            ('budget_id', '=', budget.id), ('status', '=', 'open'),
        ], limit=1)
        self.assertTrue(next_period)
        self.assertEqual(next_period.period_category_ids[0].rollover_in, 40.0)
        self.assertEqual(next_period.period_category_ids[0].effective_budget, 140.0)

    def test_close_no_rollover_when_none(self):
        _, period = self._make_budget(self.cat_expense, 100.0, rollover='none')
        self._spend(self.cat_expense, -60.0)
        period._close_period()
        self.assertEqual(self._line(period).rollover_out, 0.0)

    def test_close_skip_non_open_period(self):
        budget, period = self._make_budget(self.cat_expense, 100.0)
        period._close_period()
        open_count_before = self.env['moneta.budget.period'].search_count([
            ('budget_id', '=', budget.id), ('status', '=', 'open'),
        ])
        # Closing again is a no-op (rejection before write).
        period._close_period()
        open_count_after = self.env['moneta.budget.period'].search_count([
            ('budget_id', '=', budget.id), ('status', '=', 'open'),
        ])
        self.assertEqual(open_count_before, open_count_after)

    def test_cron_closes_expired_period(self):
        budget, period = self._make_budget(self.cat_expense, 100.0)
        period.write({'period_start': '2020-01-01', 'period_end': '2020-01-31'})
        self.env['moneta.budget.period']._cron_close_expired_periods()
        period.invalidate_recordset(['status'])
        self.assertEqual(period.status, 'closed')
        today = fields.Date.context_today(self.env.user)
        next_period = self.env['moneta.budget.period'].search([
            ('budget_id', '=', budget.id), ('status', '=', 'open'),
        ], limit=1)
        self.assertTrue(next_period)
        self.assertEqual(next_period.period_start, today.replace(day=1))

    def test_alert_levels(self):
        _, period = self._make_budget(self.cat_expense, 100.0)  # warn 80%, critical 95%
        line = self._line(period)
        self.assertEqual(line.alert_level, 'none')
        self._spend(self.cat_expense, -80.0)
        self.assertEqual(line.alert_level, 'warning')
        self._spend(self.cat_expense, -15.0)  # 95 total
        self.assertEqual(line.alert_level, 'critical')
        self._spend(self.cat_expense, -10.0)  # 105 > 100
        self.assertEqual(line.alert_level, 'over_budget')