# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestRecordRuleIsolation(MonetaTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = cls._make_user('Moneta User A', 'moneta_a')
        cls.user_b = cls._make_user('Moneta User B', 'moneta_b')
        # Each user owns one account.
        cls.account_a = cls._make_account(user=cls.user_a, name='A Checking')
        cls.account_b = cls._make_account(user=cls.user_b, name='B Checking')

    def test_user_a_sees_only_own_account(self):
        accounts = self.env['moneta.account'].with_user(self.user_a.id).search([])
        self.assertIn(self.account_a, accounts)
        self.assertNotIn(self.account_b, accounts)

    def test_user_a_cannot_read_user_b_account(self):
        with self.assertRaises(AccessError):
            self.account_b.with_user(self.user_a.id).read(['name'])

    def test_user_a_cannot_write_user_b_account(self):
        with self.assertRaises(AccessError):
            self.account_b.with_user(self.user_a.id).write({'name': 'hacked'})

    def test_transactions_are_isolated(self):
        # Create a transaction as user A on A's account.
        self.env['moneta.transaction'].with_user(self.user_a.id).create({
            'account_id': self.account_a.id,
            'amount': -10.0,
            'state': 'cleared',
        })
        # User B sees no transactions at all.
        txs_b = self.env['moneta.transaction'].with_user(self.user_b.id).search([])
        self.assertFalse(txs_b)

    def test_manager_sees_all(self):
        manager = self._make_user('Moneta Manager', 'moneta_mgr', group=self.group_manager)
        accounts = self.env['moneta.account'].with_user(manager.id).search([])
        self.assertIn(self.account_a, accounts)
        self.assertIn(self.account_b, accounts)