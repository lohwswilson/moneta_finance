# -*- coding: utf-8 -*-
"""Regression tests for the Moneta Mobile REST API authentication.

The mobile endpoints must be reachable ONLY with a valid Personal Access
Token (PAT): auth='bearer' is enforced by the framework against
`res.users.apikeys`, request.env.user is the token owner, and record rules
scope every query to that owner. The previous implementation used auth='none'
with a fallback that resolved to the Odoo admin — these tests lock in the fix.
"""
import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestMobileApiAuth(HttpCase):

    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref('moneta_finance.group_moneta_user')
        self.user_a = self._make_user('User A', 'user_a')
        self.user_b = self._make_user('User B', 'user_b')

    def _make_user(self, name, login):
        # moneta_no_seed keeps the test users' category sets deterministic,
        # matching the house convention in tests/common.py.
        return self.env['res.users'].with_context(moneta_no_seed=True).create({
            'name': name,
            'login': login,
            'email': f'{login}@example.com',
            'groups_id': [(6, 0, [self.group_user.id])],
        })

    def _make_pat(self, user, name='moneta-mobile-test'):
        """Generate a Personal Access Token owned by `user`, return plaintext.

        _generate() stamps `self.env.user` as the owner, so run it in the
        user's own env via with_user (owner = user; generating one's own
        token is the normal flow, no superuser needed). Expiration is kept
        well under the 1-day default api_key_duration so
        _check_expiration_date passes for a non-system user.
        """
        return self.env['res.users.apikeys'].with_user(user)._generate(
            None, name, fields.Datetime.now() + timedelta(hours=6))

    def _post(self, path, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return self.url_open(path, data='{}', headers=headers)

    def test_anonymous_request_rejected(self):
        """No Authorization header, no session -> the framework must refuse.

        type='json' routes report failures via the JSON-RPC error envelope
        (HTTP 200 with an `error` key), so assert on the envelope rather
        than the HTTP status.
        """
        res = self._post('/api/v1/mobile/ping')
        payload = res.json()
        self.assertIn('error', payload)
        self.assertNotIn('result', payload)

    def test_valid_pat_succeeds(self):
        key = self._make_pat(self.user_a)
        res = self._post('/api/v1/mobile/ping', token=key)
        payload = res.json()
        self.assertIn('result', payload)
        result = payload['result']
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['user_name'], self.user_a.name)

    def test_invalid_token_rejected(self):
        res = self._post('/api/v1/mobile/ping', token='deadbeef-not-a-pat')
        payload = res.json()
        self.assertIn('error', payload)
        self.assertNotIn('result', payload)

    def test_user_b_cannot_see_user_a_accounts(self):
        # user_a owns an account; user_b's PAT must see an empty list.
        self.env['moneta.account'].with_user(self.user_a).create({
            'name': 'Alice Checking',
            'account_type': 'checking',
            'currency_id': self.env.company.currency_id.id,
            'opening_balance': 1000.0,
        })
        res_b = self._post('/api/v1/mobile/accounts/list', token=self._make_pat(self.user_b))
        payload_b = res_b.json()
        self.assertIn('result', payload_b)
        self.assertEqual(payload_b['result']['accounts'], [])

        res_a = self._post('/api/v1/mobile/accounts/list', token=self._make_pat(self.user_a))
        payload_a = res_a.json()
        self.assertIn('result', payload_a)
        accounts = payload_a['result']['accounts']
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]['name'], 'Alice Checking')
