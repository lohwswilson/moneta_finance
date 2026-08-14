# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date
from ..models.ai_advisor import MonetaAIClient


class TestAIFeatures(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.account = self.env['moneta.account'].create({
            'name': 'Primary Checking',
            'account_type': 'chequing',
            'opening_balance': 2500.0,
        })
        self.category = self.env['moneta.category'].create({
            'name': 'Groceries',
            'is_income': False,
        })

    def test_ai_advisor_fallback(self):
        """Test fallback advisory message when no external API key is set."""
        resp = MonetaAIClient.generate_text(self.env, "You are a financial advisor.", "How do I save money?")
        self.assertIn("Moneta AI Wealth Advisor", resp)
        self.assertIn("Key Financial Principles", resp)

    def test_ai_chat_session(self):
        """Test chat session context building and message flow."""
        chat = self.env['moneta.ai.chat'].create({
            'name': 'Retirement Planning',
            'pending_question': 'How is my net worth doing?',
        })
        chat.action_send_message()
        self.assertEqual(len(chat.message_ids), 2)
        self.assertEqual(chat.message_ids[0].role, 'user')
        self.assertEqual(chat.message_ids[1].role, 'assistant')

    def test_ai_receipt_wizard(self):
        """Test receipt OCR wizard parsing and transaction creation."""
        wiz = self.env['moneta.ai.receipt.wizard'].create({
            'account_id': self.account.id,
            'receipt_file': b'dummy_receipt_data',
            'file_name': 'receipt.jpg',
        })
        wiz.action_scan_receipt()
        self.assertEqual(wiz.state, 'review')
        self.assertTrue(bool(wiz.merchant_name))
        self.assertTrue(len(wiz.line_ids) > 0)

        # Create Transaction
        action = wiz.action_create_transaction()
        tx = self.env['moneta.transaction'].browse(action['res_id'])
        self.assertEqual(tx.account_id.id, self.account.id)
        self.assertTrue(tx.is_split)
        self.assertEqual(tx.state, 'cleared')

    def test_ai_transaction_enrich(self):
        """Test transaction AI enrichment action."""
        tx = self.env['moneta.transaction'].create({
            'account_id': self.account.id,
            'amount': -35.0,
            'memo': 'SQ *BLUE BOTTLE COFFEE SF CA',
            'transaction_date': date(2026, 8, 1),
        })
        tx.action_ai_enrich()
        self.assertEqual(tx.amount, -35.0)
