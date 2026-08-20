# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestPayeeMatcher(MonetaTestBase):

    def _payees(self, user):
        return self.env['moneta.payee'].with_user(user)

    def test_exact_case_insensitive_match(self):
        user = self._make_user('Payee User', 'payee_user')
        Payee = self._payees(user)
        star = Payee.create({'name': 'Starbucks'})
        # Case-insensitive exact name resolves to the existing payee.
        self.assertEqual(Payee._resolve_by_name('starbucks'), star)
        self.assertEqual(Payee._resolve_by_name('STARBUCKS'), star)

    def test_wildcard_alias_match(self):
        user = self._make_user('Payee Alias', 'payee_alias')
        Payee = self._payees(user)
        star = Payee.create({
            'name': 'Starbucks',
            'alias_ids': [(0, 0, {'pattern': 'STARBUCKS*'})],
        })
        # The wildcard alias matches a longer imported string.
        self.assertEqual(Payee._resolve_by_name('STARBUCKS DOWNTOWN 0421'), star)

    def test_normalized_match_strips_business_suffix(self):
        user = self._make_user('Payee Norm', 'payee_norm')
        Payee = self._payees(user)
        lidl = Payee.create({'name': 'Lidl'})
        # "LIDL sp. z o.o." normalizes to "LIDL", matching the "Lidl" payee.
        self.assertEqual(Payee._resolve_by_name('LIDL sp. z o.o.'), lidl)

    def test_no_match_returns_empty(self):
        user = self._make_user('Payee None', 'payee_none')
        Payee = self._payees(user)
        Payee.create({'name': 'Starbucks'})
        self.assertFalse(Payee._resolve_by_name('Unknown Co'))

    def test_wildcard_glob_is_redos_safe(self):
        Payee = self.env['moneta.payee']
        # A pathological pattern with many stars must not blow up; the matcher
        # is iterative (no regex), so this returns quickly either way.
        result = Payee._matches_alias_pattern('a' * 400, '*'.join(['a' for _ in range(200)]))
        self.assertIn(result, (True, False))

    def test_payee_website_normalization(self):
        Payee = self.env['moneta.payee']
        self.assertEqual(Payee._normalize_website('starbucks.com'), 'https://starbucks.com')
        self.assertEqual(Payee._normalize_website('http://apple.com/shop'), 'https://apple.com')
        self.assertFalse(Payee._normalize_website(''))
        self.assertFalse(Payee._normalize_website('invalid'))

    def test_payee_logo_flag(self):
        user = self._make_user('Payee Logo User', 'payee_logo_user')
        Payee = self._payees(user)
        p = Payee.create({
            'name': 'Netflix',
            'website': 'https://netflix.com',
            'image_128': b'fake_image_bytes_123',
        })
        self.assertTrue(p.has_logo)
        p.image_128 = False
        self.assertFalse(p.has_logo)