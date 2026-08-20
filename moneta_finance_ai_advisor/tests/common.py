# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import TransactionCase


class MonetaTestBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.company.currency_id
        cls.group_user = cls.env.ref('moneta_finance.group_moneta_user')
        cls.group_manager = cls.env.ref('moneta_finance.group_moneta_manager')
        cls.cat_expense = cls.env['moneta.category'].create({
            'name': 'Test Expense', 'is_income': False,
        })
        cls.cat_income = cls.env['moneta.category'].create({
            'name': 'Test Income', 'is_income': True,
        })

    @classmethod
    def _make_user(cls, name, login, group=None):
        group = group or cls.group_user
        return cls.env['res.users'].with_context(moneta_no_seed=True).create({
            'name': name,
            'login': login,
            'email': f'{login}@example.com',
            'groups_id': [(6, 0, [group.id])],
        })

    @classmethod
    def _make_account(cls, user=None, **kw):
        vals = {
            'name': kw.pop('name', 'Test Account'),
            'account_type': kw.pop('account_type', 'checking'),
            'currency_id': kw.pop('currency_id', cls.currency.id),
            'opening_balance': kw.pop('opening_balance', 0.0),
        }
        vals.update(kw)
        env = cls.env['moneta.account'].with_user(user.id) if user else cls.env['moneta.account']
        return env.create(vals)

    @classmethod
    def _make_transaction(cls, account, amount, user=None, **kw):
        vals = {
            'account_id': account.id,
            'amount': amount,
            'transaction_date': kw.pop('transaction_date', fields.Date.context_today(cls.env.user)),
            'state': kw.pop('state', 'cleared'),
        }
        vals.update(kw)
        env = cls.env['moneta.transaction'].with_user(user.id) if user else cls.env['moneta.transaction']
        return env.create(vals)
