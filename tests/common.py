# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import TransactionCase


class MonetaTestBase(TransactionCase):
    """Base class for Moneta tests: a currency, the Moneta user group, and
    helpers to mint users/accounts and read balances straight from the DB
    (the balance fields are maintained by raw SQL, so the ORM cache must be
    invalidated before each assertion)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.company.currency_id
        cls.group_user = cls.env.ref('moneta_finance.group_moneta_user')
        cls.group_manager = cls.env.ref('moneta_finance.group_moneta_manager')
        # A couple of categories for split / budget tests. Created without
        # is_system so tests can delete them; is_income carries the type.
        cls.cat_expense = cls.env['moneta.category'].create({
            'name': 'Test Expense', 'is_income': False,
        })
        cls.cat_income = cls.env['moneta.category'].create({
            'name': 'Test Income', 'is_income': True,
        })

    @classmethod
    def _make_user(cls, name, login, group=None):
        group = group or cls.group_user
        # moneta_no_seed keeps test users' category sets deterministic (empty
        # unless a test seeds explicitly) instead of pulling in the 30-template
        # default set the res.users hook would otherwise copy.
        return cls.env['res.users'].with_context(moneta_no_seed=True).create({
            'name': name,
            'login': login,
            'email': f'{login}@example.com',
            'groups_id': [(6, 0, [group.id])],
        })

    # Classmethods so both `self._make_account(...)` and
    # `cls._make_account(...)` (setUpClass) work; `user=` scopes the create to
    # that owner (record rules keep the data per-user).
    @classmethod
    def _make_account(cls, user=None, **kw):
        vals = {
            'name': kw.pop('name', 'Test Account'),
            'account_type': kw.pop('account_type', 'chequing'),
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

    def _current_balance(self, account):
        # The balance is written by raw SQL; invalidate the cache so we read
        # the value the database actually holds, not a stale cached figure.
        account.invalidate_recordset(['current_balance', 'cleared_balance'])
        return round(account.current_balance or 0.0, 4)

    def _cleared_balance(self, account):
        account.invalidate_recordset(['current_balance', 'cleared_balance'])
        return round(account.cleared_balance or 0.0, 4)