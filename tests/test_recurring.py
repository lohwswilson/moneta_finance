# -*- coding: utf-8 -*-
from datetime import date
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestRecurring(MonetaTestBase):

    def test_post_creates_transaction_and_advances_next_date(self):
        acc = self._make_account(opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        sched = self.env['moneta.recurring.transaction'].create({
            'name': 'Rent',
            'account_id': acc.id,
            'amount': -1200.0,
            'frequency': 'monthly',
            'next_date': today,
        })
        sched.post()
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertEqual(len(txs), 1)
        self.assertEqual(round(txs[0].amount, 4), -1200.0)
        self.assertEqual(txs[0].transaction_date, today)
        # next_date advanced past today.
        self.assertGreater(sched.next_date, today)
        self.assertEqual(sched.last_posted_date, today)

    def test_once_self_deletes_after_post(self):
        acc = self._make_account(opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        sched = self.env['moneta.recurring.transaction'].create({
            'name': 'One-off',
            'account_id': acc.id,
            'amount': -50.0,
            'frequency': 'once',
            'next_date': today,
        })
        sched.post()
        self.assertFalse(sched.exists())
        # The transaction was still created.
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertEqual(len(txs), 1)

    def test_skip_advances_without_creating(self):
        acc = self._make_account(opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        sched = self.env['moneta.recurring.transaction'].create({
            'name': 'Subscription',
            'account_id': acc.id,
            'amount': -15.0,
            'frequency': 'monthly',
            'next_date': today,
        })
        original_next = sched.next_date
        sched.skip()
        self.assertNotEqual(sched.next_date, original_next)
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertFalse(txs)

    def test_calculate_next_due_date_month_clamp(self):
        # Jan 31 + 1 month -> Feb 28 (clamp to month length).
        self.assertEqual(
            self.env['moneta.recurring.transaction']._calculate_next_due_date(
                date(2026, 1, 31), 'monthly'),
            date(2026, 2, 28),
        )

    def test_calculate_next_due_date_semimonthly(self):
        # Day <= 15 -> last day of current month.
        self.assertEqual(
            self.env['moneta.recurring.transaction']._calculate_next_due_date(
                date(2026, 2, 10), 'semimonthly'),
            date(2026, 2, 28),
        )
        # Day > 15 -> 15th of next month.
        self.assertEqual(
            self.env['moneta.recurring.transaction']._calculate_next_due_date(
                date(2026, 2, 20), 'semimonthly'),
            date(2026, 3, 15),
        )

    def test_auto_post_cron(self):
        acc = self._make_account(opening_balance=0.0)
        today = fields.Date.context_today(self.env.user)
        sched = self.env['moneta.recurring.transaction'].create({
            'name': 'Auto Rent',
            'account_id': acc.id,
            'amount': -900.0,
            'frequency': 'monthly',
            'next_date': today,
            'auto_post': True,
        })
        self.env['moneta.recurring.transaction']._cron_auto_post()
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertEqual(len(txs), 1)
        self.assertGreater(sched.next_date, today)