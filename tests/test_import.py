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
    def test_dbs_bank_csv_import(self):
        acc = self._make_account(opening_balance=0.0)
        dbs_csv = (
            "Transaction Date,Value Date,Statement Code,Description,Supplementary Code,Supplementary Code Description,Client Reference,Additional Reference,Status,Currency,Debit Amount,Credit Amount\n"
            "31-Jul-26,,ATINT,   , ,Interest Earned,,,Settled,SGD,,0.31\n"
            "31-Jul-26,,ATFEE,   , ,Account Fee,,,Settled,SGD,2,\n"
            "31-Jul-26,,ATM,\"CSH 31200469,PEOPLE PK FC  \",\"CSH 31200469,PEOPLE PK FC\",ATM,,,Settled,SGD,100,\n"
            "20-Jul-26,,ADV,ICT Incoming PayNow Ref 5877687 From: LIEW WAI KUAN OTHR Travel insurance claims,ICT Incoming PayNow Ref 5877687,Advice,From: LIEW WAI KUAN,OTHR Travel insurance claims,Settled,SGD,,419\n"
        )
        wiz = self._wizard(acc, 'csv', dbs_csv)
        wiz.action_import()
        txs = self.env['moneta.transaction'].search([('account_id', '=', acc.id)], order='transaction_date desc')
        self.assertEqual(len(txs), 4)
        
        # Check interest deposit
        int_tx = txs.filtered(lambda t: t.amount == 0.31)
        self.assertTrue(int_tx)
        self.assertEqual(str(int_tx.transaction_date), '2026-07-31')
        self.assertEqual(int_tx.payee_id.name, 'Interest Earned')

        # Check fee withdrawal
        fee_tx = txs.filtered(lambda t: t.amount == -2.0)
        self.assertTrue(fee_tx)
        self.assertEqual(fee_tx.payee_id.name, 'Account Fee')

        # Check PayNow
        paynow_tx = txs.filtered(lambda t: t.amount == 419.0)
        self.assertTrue(paynow_tx)
        self.assertEqual(str(paynow_tx.transaction_date), '2026-07-20')
        self.assertEqual(paynow_tx.payee_id.name, 'LIEW WAI KUAN')
