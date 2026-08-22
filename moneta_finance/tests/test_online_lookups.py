# -*- coding: utf-8 -*-
"""Gating tests for the core's external network calls.

The core is offline-first and deterministic by design: every outbound HTTP
call (Yahoo Finance quotes, Google favicons) is gated behind the opt-in
'Moneta Settings > Online Features > Online lookups' parameter
(moneta_finance.online_lookups, default off) and NEVER runs on a write path.
These tests assert the gate holds even if a future change forgets the flag.
"""
from unittest.mock import patch

from odoo.exceptions import ValidationError

from .common import MonetaTestBase


class TestOnlineLookupGating(MonetaTestBase):

    def _set_online(self, value):
        self.env['ir.config_parameter'].set_param(
            'moneta_finance.online_lookups', value)

    def test_lookup_disabled_by_default_returns_empty_and_no_network(self):
        with patch('urllib.request.urlopen',
                   side_effect=AssertionError('network must not be called')) as urlopen:
            info = self.env['moneta.security']._lookup_symbol_info('AAPL')
        urlopen.assert_not_called()
        self.assertEqual(info, {})

    def test_lookup_enabled_uses_network(self):
        self._set_online('True')
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"chart":{"result":[{"meta":{'
                b'"shortName":"Apple Inc","regularMarketPrice":190.5,'
                b'"chartPreviousClose":188.0}}]}}'
            )
            info = self.env['moneta.security']._lookup_symbol_info('AAPL')
        urlopen.assert_called_once()
        self.assertEqual(info['name'], 'Apple Inc')
        self.assertAlmostEqual(info['price'], 190.5)

    def test_payee_create_never_touches_network_even_when_enabled(self):
        self._set_online('True')
        with patch('urllib.request.urlopen',
                   side_effect=AssertionError('network must not be called')) as urlopen:
            payee = self.env['moneta.payee'].create({
                'name': 'TestCo',
                'website': 'testco.example',
            })
        urlopen.assert_not_called()
        self.assertFalse(payee.image_128)

    def test_fetch_favicon_disabled_raises(self):
        self._set_online('False')
        payee = self.env['moneta.payee'].create({'name': 'TestCo'})
        with self.assertRaises(ValidationError):
            payee.action_fetch_favicon()

    def test_fetch_quote_disabled_raises(self):
        self._set_online('False')
        security = self.env['moneta.security'].create({'symbol': 'AAPL', 'name': 'Apple Inc'})
        with self.assertRaises(ValidationError):
            security.action_fetch_quote()
