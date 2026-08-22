# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestReconciliation(MonetaTestBase):

    def test_mark_cleared_moves_to_cleared_balance(self):
        acc = self._make_account(opening_balance=100.0)
        tx = self._make_transaction(acc, -40.0, state='unreconciled')
        self.assertEqual(self._current_balance(acc), 60.0)
        self.assertEqual(self._cleared_balance(acc), 100.0)  # not cleared yet
        tx.action_mark_cleared()
        self.assertEqual(tx.state, 'cleared')
        self.assertEqual(self._cleared_balance(acc), 60.0)

    def test_reconcile_stamps_reconciled_date(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -10.0, state='cleared')
        today = fields.Date.context_today(self.env.user)
        tx.action_reconcile()
        self.assertEqual(tx.state, 'reconciled')
        self.assertEqual(tx.reconciled_date, today)

    def test_reconcile_keeps_existing_date(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -10.0, state='reconciled', reconciled_date='2026-01-15')
        tx.action_reconcile()
        # Odoo 18 Date fields read back as datetime.date, not strings.
        self.assertEqual(tx.reconciled_date, fields.Date.to_date('2026-01-15'))

    def test_unreconcile_clears_date(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -10.0, state='reconciled', reconciled_date='2026-01-15')
        tx.action_unreconcile()
        self.assertEqual(tx.state, 'unreconciled')
        self.assertFalse(tx.reconciled_date)

    def test_void_transactions_refused(self):
        acc = self._make_account(opening_balance=0.0)
        tx = self._make_transaction(acc, -10.0, state='void')
        with self.assertRaises(ValidationError):
            tx.action_reconcile()
        with self.assertRaises(ValidationError):
            tx.action_mark_cleared()
        with self.assertRaises(ValidationError):
            tx.action_unreconcile()
        # Rejection before write: the state is untouched.
        self.assertEqual(tx.state, 'void')

    def test_reconcile_does_not_propagate_to_transfer_counterpart(self):
        # Monize v1.15.0 parity: transfer reconciliation status is independent
        # per account -- reconciling one leg does NOT force a state on the
        # counterpart (the old pair-wide propagation was deliberately removed).
        acc1 = self._make_account(name='Checking', opening_balance=0.0)
        acc2 = self._make_account(name='Savings', opening_balance=0.0)
        tx = self._make_transaction(acc1, -200.0, is_transfer=True, transfer_account_id=acc2.id)
        cp = tx.linked_transaction_id
        cp_state_before = cp.state
        tx.action_reconcile()
        self.assertEqual(tx.state, 'reconciled')
        self.assertEqual(cp.state, cp_state_before)

    # ------------------------------------------------------------------
    # Reconciliation wizard -- the cleared-balance math.
    # ------------------------------------------------------------------

    def _open_wizard(self, account):
        return self.env['moneta.reconciliation.wizard'].with_context(
            default_account_id=account.id,
        ).create({})

    def test_wizard_cleared_balance_starts_from_opening_cleared(self):
        """The wizard's cleared balance must start from opening_cleared_balance
        (prior cleared + reconciled already baked in) and add only the
        newly-ticked unreconciled lines -- not re-sum every ticked line and not
        drop the prior reconciled transactions (the old formula did both)."""
        acc = self._make_account(opening_balance=1000.0)
        # Prior reconciled deposit: in account.cleared_balance, NOT a wizard line.
        self._make_transaction(acc, 500.0, state='reconciled',
                               reconciled_date=fields.Date.context_today(self.env.user))
        # Prior cleared payment: in account.cleared_balance, loaded ticked.
        self._make_transaction(acc, -200.0, state='cleared')
        # Two unreconciled transactions the user will tick this session.
        tx_dep = self._make_transaction(acc, 300.0, state='unreconciled')
        tx_pay = self._make_transaction(acc, -100.0, state='unreconciled')

        # opening(1000) + reconciled(500) + cleared(-200) = 1300.
        self.assertEqual(self._cleared_balance(acc), 1300.0)

        wizard = self._open_wizard(acc)
        self.assertEqual(round(wizard.opening_cleared_balance, 4), 1300.0)
        # Reconciled is excluded; cleared + 2 unreconciled are loaded.
        self.assertEqual(len(wizard.line_ids), 3)

        # Tick just the +300 unreconciled deposit.
        wizard.line_ids.filtered(lambda l: l.transaction_id.id == tx_dep.id).is_cleared = True
        wizard.invalidate_recordset()
        # 1300 + 300 = 1600. The -200 cleared line is already in the base (not
        # re-added); the +500 reconciled stays in the base (not dropped). The
        # old formula returned 1000 + (300 - 200) = 1100 -- wrong on both counts.
        self.assertEqual(round(wizard.cleared_deposits_total, 4), 300.0)
        self.assertEqual(round(wizard.cleared_payments_total, 4), 0.0)
        self.assertEqual(round(wizard.cleared_balance, 4), 1600.0)
        wizard.statement_ending_balance = 1600.0
        wizard.invalidate_recordset()
        self.assertEqual(round(wizard.difference, 4), 0.0)

        # Tick the -100 unreconciled payment too -> 1300 + 300 - 100 = 1500.
        wizard.line_ids.filtered(lambda l: l.transaction_id.id == tx_pay.id).is_cleared = True
        wizard.invalidate_recordset()
        self.assertEqual(round(wizard.cleared_payments_total, 4), 100.0)
        self.assertEqual(round(wizard.cleared_balance, 4), 1500.0)

    def test_wizard_unclearing_a_prior_cleared_line_keeps_balance(self):
        """Unticking a previously-cleared line must NOT lower the cleared
        balance: it stays cleared (only its promotion to reconciled is
        skipped), so it remains counted in opening_cleared_balance."""
        acc = self._make_account(opening_balance=500.0)
        tx_cl = self._make_transaction(acc, -50.0, state='cleared')   # in base
        self._make_transaction(acc, 120.0, state='unreconciled')      # tick later
        self.assertEqual(self._cleared_balance(acc), 450.0)           # 500 - 50

        wizard = self._open_wizard(acc)
        self.assertEqual(round(wizard.opening_cleared_balance, 4), 450.0)
        # Untick the prior-cleared line; tick the unreconciled deposit.
        wizard.line_ids.filtered(lambda l: l.transaction_id.id == tx_cl.id).is_cleared = False
        dep_line = wizard.line_ids.filtered(lambda l: l.transaction_id.state == 'unreconciled')
        dep_line.is_cleared = True
        wizard.invalidate_recordset()
        # 450 + 120 = 570. Unticking the cleared line does not remove it (still
        # cleared, still in the base); only the unreconciled deposit is added.
        self.assertEqual(round(wizard.cleared_balance, 4), 570.0)