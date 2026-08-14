# -*- coding: utf-8 -*-
import base64
from odoo import fields
from odoo.tests import tagged

from .common import MonetaTestBase


@tagged('post_install', '-at_install')
class TestImport(MonetaTestBase):

    OFX_SGML = (
        "<OFXHEADER:100>\n"
        "DATA:OFXSGML\n"
        "<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>\n"
        "<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260801<TRNAMT>-42.50<FITID>1<NAME>COFFEE SHOP<MEMO>LATTE</STMTTRN>\n"
        "<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260802<TRNAMT>2500.00<FITID>2<NAME>EMPLOYEE PAYROLL</STMTTRN>\n"
        "</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>\n"
    )

    def _wizard(self, account, file_type, content):
        return self.env['moneta.import.wizard'].create({
            'account_id': account.id,
            'file_type': file_type,
            'file_data': base64.b64encode(content.encode('utf-8')),
            'file_name': f'sample.{file_type}',
        })

    def test_ofx_parse_creates_transactions(self):
        acc = self._make_account(opening_balance=0.0)
        wiz = self._wizard(acc, 'ofx', self.OFX_SGML)
        wiz.action_import()
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertEqual(len(txs), 2)
        amounts = sorted(round(t.amount, 4) for t in txs)
        self.assertEqual(amounts, [-42.5, 2500.0])
        # Payee captured from NAME.
        coffee = self.env['moneta.payee'].search([('name', 'ilike', 'COFFEE SHOP')])
        self.assertTrue(coffee)

    def test_qif_opening_balance_seeds_account(self):
        acc = self._make_account(opening_balance=0.0)
        qif = (
            "!Type:Bank\n"
            "D2026-08-01\n"
            "T1500.00\n"
            "POpening Balance\n"
            "^\n"
        )
        wiz = self._wizard(acc, 'qif', qif)
        wiz.action_import()
        # Opening balance row sets the account opening balance, no transaction created.
        self.assertEqual(self._current_balance(acc), 1500.0)
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertFalse(txs)

    def test_csv_parse_creates_transaction(self):
        acc = self._make_account(opening_balance=0.0)
        csv_content = "Date,Payee,Amount,Memo\n2026-08-03,Grocery Store,-55.20,Weekly\n"
        wiz = self._wizard(acc, 'csv', csv_content)
        wiz.action_import()
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)])
        self.assertEqual(len(txs), 1)
        self.assertEqual(round(txs[0].amount, 4), -55.2)