# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import MonetaTestBase


# Moneta refuses to delete an account that still has transactions or investment
# transactions ("Cannot delete account with N transaction(s). Close the account
# instead."), and refuses to delete a category that is_system, has
# subcategories, or is referenced by transactions / split lines / scheduled
# transactions ("Reassign transactions first."). The Odoo port must refuse the
# same writes before super().unlink() runs -- without these guards the ORM's
# ondelete='cascade' (parent_id) and ondelete='set null' (category_id) silently
# destroy or detach the referencing rows, which is data loss the user is not
# warned about.


@tagged('post_install', '-at_install')
class TestAccountDeleteGuard(MonetaTestBase):

    def test_account_with_transaction_refuses_delete(self):
        acc = self._make_account(opening_balance=0.0)
        self._make_transaction(acc, -100.0)
        with self.assertRaises(ValidationError):
            acc.unlink()

    def test_account_with_investment_transaction_refuses_delete(self):
        acc = self._make_account(account_type='brokerage', opening_balance=0.0)
        sec = self.env['moneta.security'].create({'name': 'Test Inc', 'symbol': 'TST'})
        self.env['moneta.investment.transaction'].create({
            'action': 'buy',
            'account_id': acc.id,
            'security_id': sec.id,
            'trade_date': fields.Date.context_today(self.env.user),
            'quantity': 1.0,
            'price': 10.0,
        })
        with self.assertRaises(ValidationError):
            acc.unlink()

    def test_empty_account_deletes(self):
        acc = self._make_account(opening_balance=0.0)
        acc_id = acc.id
        acc.unlink()
        self.assertFalse(self.env['moneta.account'].browse(acc_id).exists())


@tagged('post_install', '-at_install')
class TestCategoryDeleteGuard(MonetaTestBase):

    def test_category_with_subcategory_refuses_delete(self):
        parent = self.env['moneta.category'].create({'name': 'Parent Cat'})
        self.env['moneta.category'].create({'name': 'Child Cat', 'parent_id': parent.id})
        with self.assertRaises(ValidationError):
            parent.unlink()

    def test_category_with_transaction_refuses_delete(self):
        cat = self.env['moneta.category'].create({'name': 'Used Cat'})
        acc = self._make_account(opening_balance=0.0)
        self._make_transaction(acc, -50.0, category_id=cat.id)
        with self.assertRaises(ValidationError):
            cat.unlink()

    def test_category_with_split_refuses_delete(self):
        cat = self.env['moneta.category'].create({'name': 'Split Cat'})
        acc = self._make_account(opening_balance=0.0)
        self.env['moneta.transaction'].create({
            'account_id': acc.id,
            'amount': -80.0,
            'is_split': True,
            'state': 'cleared',
            'split_ids': [(0, 0, {'category_id': cat.id, 'amount': -80.0})],
        })
        with self.assertRaises(ValidationError):
            cat.unlink()

    def test_category_with_scheduled_transaction_refuses_delete(self):
        cat = self.env['moneta.category'].create({'name': 'Recurring Cat'})
        acc = self._make_account(opening_balance=0.0)
        self.env['moneta.recurring.transaction'].create({
            'name': 'Subscription',
            'account_id': acc.id,
            'category_id': cat.id,
            'amount': -10.0,
            'frequency': 'monthly',
            'next_date': fields.Date.context_today(self.env.user),
        })
        with self.assertRaises(ValidationError):
            cat.unlink()

    def test_unused_category_deletes(self):
        cat = self.env['moneta.category'].create({'name': 'Free Cat'})
        cat_id = cat.id
        cat.unlink()
        self.assertFalse(self.env['moneta.category'].browse(cat_id).exists())

    def test_system_category_refuses_delete(self):
        # Existing guard: is_system categories are archived, not deleted.
        sys_cat = self.env['moneta.category'].create({'name': 'Sys Cat', 'is_system': True})
        with self.assertRaises(ValidationError):
            sys_cat.unlink()