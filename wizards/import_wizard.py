# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

_OFX_FIELD_RE = re.compile(r'<([A-Z0-9.]+)>([^<\r\n]*)', re.IGNORECASE)


class MonetaImportWizard(models.TransientModel):
    _name = 'moneta.import.wizard'
    _description = 'Moneta Financial File Import Wizard (QIF / OFX / CSV / Bank Profiles)'

    account_id = fields.Many2one('moneta.account', string='Target Account', required=True)
    file_type = fields.Selection([
        ('csv', 'CSV File (Bank Statements, DBS, OCBC, UOB, Quicken, Excel)'),
        ('qif', 'QIF (Quicken / MS Money)'),
        ('ofx', 'OFX / QFX (Open Financial Exchange)')
    ], string='File Type', default='csv', required=True)

    bank_profile = fields.Selection([
        ('auto', 'Universal Smart Auto-Detect (Any Bank)'),
        ('dbs_posb', 'DBS / POSB Bank (Singapore)'),
        ('ocbc', 'OCBC Bank (Singapore)'),
        ('uob', 'UOB United Overseas Bank (Singapore)'),
        ('citi', 'Citibank (Singapore & Global)'),
        ('sc', 'Standard Chartered Bank'),
        ('hsbc', 'HSBC Bank'),
        ('wise', 'Wise (TransferWise)'),
        ('revolut', 'Revolut Multi-Currency'),
        ('chase', 'Chase Bank (US)'),
        ('bofa', 'Bank of America (US)'),
        ('amex', 'American Express (Global)'),
        ('maybank', 'Maybank / CIMB'),
        ('custom', 'Custom CSV Mapping Preset'),
    ], string='Bank Format Profile', default='auto', required=True,
       help='Select your bank format profile or let Moneta automatically detect the statement columns.')

    file_data = fields.Binary(string='Upload Statement File', required=True)
    file_name = fields.Char(string='File Name')

    skip_duplicates = fields.Boolean(string='Skip Duplicate Transactions', default=True, help='Skip transactions that match existing records on same account, date, and amount.')
    apply_rules = fields.Boolean(string='Apply Automation Rules', default=True, help='Automatically categorize and tag transactions using your configured Transaction Rules.')

    imported_count = fields.Integer(string='Imported Transactions Count', readonly=True)
    skipped_count = fields.Integer(string='Skipped Duplicates Count', readonly=True)

    # CSV column mapping (editable step: auto-detect with override). Columns
    # are 1-based; 0 means "auto-detect" at import time.
    csv_has_header = fields.Boolean(string='CSV Has Header Row', default=True)
    csv_date_col = fields.Integer(string='Date Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_payee_col = fields.Integer(string='Payee / Description Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_amount_col = fields.Integer(string='Amount Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_debit_col = fields.Integer(string='Debit / Withdrawal Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_credit_col = fields.Integer(string='Credit / Deposit Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_category_col = fields.Integer(string='Category Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_memo_col = fields.Integer(string='Memo / Ref Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_column_count = fields.Integer(string='Detected Columns', readonly=True)
    csv_preview = fields.Text(string='File Preview', readonly=True)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )

    @api.onchange('account_id')
    def _onchange_account_id(self):
        """Auto-populate bank profile from linked institution or account name."""
        if self.account_id:
            if self.account_id.institution_id and self.account_id.institution_id.bank_profile:
                self.bank_profile = self.account_id.institution_id.bank_profile
            elif 'dbs' in self.account_id.name.lower() or 'posb' in self.account_id.name.lower():
                self.bank_profile = 'dbs_posb'
            elif 'ocbc' in self.account_id.name.lower():
                self.bank_profile = 'ocbc'
            elif 'uob' in self.account_id.name.lower():
                self.bank_profile = 'uob'
            elif 'wise' in self.account_id.name.lower():
                self.bank_profile = 'wise'
            elif 'revolut' in self.account_id.name.lower():
                self.bank_profile = 'revolut'

    def action_detect_csv(self):
        """Parse the uploaded CSV, apply bank profile or auto-detect mapping, and fill fields."""
        self.ensure_one()
        if not self.file_data:
            raise UserError("Upload a CSV file first, then detect the columns.")
        content = base64.b64decode(self.file_data).decode('utf-8-sig', errors='ignore')
        rows, has_header, mapping = self._detect_csv_mapping(content, profile=self.bank_profile)
        width = max((len(r) for r in rows), default=0)
        self.write({
            'csv_has_header': has_header,
            'csv_date_col': mapping['date'] + 1 if mapping['date'] >= 0 else 0,
            'csv_payee_col': mapping['payee'] + 1 if mapping['payee'] >= 0 else 0,
            'csv_amount_col': mapping['amount'] + 1 if mapping['amount'] >= 0 else 0,
            'csv_debit_col': mapping['debit'] + 1 if mapping['debit'] >= 0 else 0,
            'csv_credit_col': mapping['credit'] + 1 if mapping['credit'] >= 0 else 0,
            'csv_category_col': mapping['category'] + 1 if mapping['category'] >= 0 else 0,
            'csv_memo_col': mapping['memo'] + 1 if mapping['memo'] >= 0 else 0,
            'csv_column_count': width,
            'csv_preview': '\n'.join(','.join(r) for r in rows[:6]),
        })
        return True

    def action_import(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError("Please upload a file to import.")

        if self.file_name and self.file_name.lower().endswith('.qdf'):
            raise UserError(
                "Quicken .QDF files are proprietary encrypted binary database files and cannot be read directly.\n\n"
                "How to import your Quicken data into Moneta:\n"
                "1. In Quicken, open your file and go to: File -> File Export -> QIF File...\n"
                "2. Check 'Transactions', 'Account List', and 'Category List', then click Export.\n"
                "3. Save the exported .QIF file on your computer.\n"
                "4. Return here, select 'QIF (Quicken / MS Money)', and upload your .QIF file!"
            )

        try:
            content = base64.b64decode(self.file_data).decode('utf-8-sig', errors='ignore')
        except Exception as e:
            raise UserError(f"Unable to read file: {e}")

        if self.file_type == 'csv':
            count, skipped = self._parse_csv(content)
        elif self.file_type == 'qif':
            count, skipped = self._parse_qif(content), 0
        elif self.file_type == 'ofx':
            count, skipped = self._parse_ofx(content), 0
        else:
            raise UserError("Unsupported file type.")

        self.imported_count = count
        self.skipped_count = skipped
        
        msg = f"Successfully imported {count} transaction(s) into {self.account_id.name}."
        if skipped > 0:
            msg += f" (Skipped {skipped} duplicate entries)."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Completed',
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _detect_csv_mapping(self, content, profile='auto'):
        """Return (rows, has_header, mapping) for a CSV file.
        Applies bank-specific profiles (DBS, OCBC, UOB, Wise, Revolut, etc.) or smart auto-detection."""
        reader = csv.reader(io.StringIO(content))
        rows = [r for r in reader if r]
        mapping = {'date': -1, 'payee': -1, 'amount': -1, 'debit': -1, 'credit': -1, 'category': -1, 'memo': -1}
        if not rows:
            return rows, False, mapping

        header = [c.lower().strip() for c in rows[0]]
        has_header = any(
            k in ' '.join(header)
            for k in ['date', 'payee', 'description', 'amount', 'debit', 'credit', 'category', 'status', 'currency', 'reference', 'withdrawal', 'deposit']
        )

        # 1. Bank Profile Specific Detection
        if profile == 'dbs_posb' or (profile == 'auto' and 'statement code' in header and 'supplementary code' in header):
            for idx, col in enumerate(header):
                if 'transaction date' in col or ('date' in col and 'value' not in col and mapping['date'] == -1):
                    mapping['date'] = idx
                elif col == 'description' or (mapping['payee'] == -1 and 'description' in col and 'supplementary' not in col):
                    mapping['payee'] = idx
                elif 'debit amount' in col or col == 'debit':
                    mapping['debit'] = idx
                elif 'credit amount' in col or col == 'credit':
                    mapping['credit'] = idx
                elif 'additional reference' in col or 'client reference' in col:
                    mapping['memo'] = idx
            return rows, True, mapping

        elif profile == 'ocbc' or (profile == 'auto' and any('withdrawals (' in h for h in header)):
            for idx, col in enumerate(header):
                if 'transaction date' in col or ('date' in col and 'value' not in col and mapping['date'] == -1):
                    mapping['date'] = idx
                elif 'description' in col:
                    mapping['payee'] = idx
                elif 'withdrawal' in col:
                    mapping['debit'] = idx
                elif 'deposit' in col:
                    mapping['credit'] = idx
            return rows, True, mapping

        elif profile == 'uob' or (profile == 'auto' and 'transaction description' in header and 'available balance' in header):
            for idx, col in enumerate(header):
                if 'transaction date' in col or 'date' in col:
                    mapping['date'] = idx
                elif 'transaction description' in col or 'description' in col:
                    mapping['payee'] = idx
                elif 'withdrawal' in col or 'debit' in col:
                    mapping['debit'] = idx
                elif 'deposit' in col or 'credit' in col:
                    mapping['credit'] = idx
            return rows, True, mapping

        elif profile == 'wise' or (profile == 'auto' and 'transferwise id' in header):
            for idx, col in enumerate(header):
                if 'date' in col:
                    mapping['date'] = idx
                elif 'description' in col or 'target name' in col:
                    mapping['payee'] = idx
                elif 'amount' in col and mapping['amount'] == -1:
                    mapping['amount'] = idx
                elif 'payment reference' in col:
                    mapping['memo'] = idx
            return rows, True, mapping

        elif profile == 'revolut' or (profile == 'auto' and 'started date' in header and 'completed date' in header):
            for idx, col in enumerate(header):
                if 'completed date' in col or 'started date' in col:
                    if mapping['date'] == -1 or 'completed' in col:
                        mapping['date'] = idx
                elif 'description' in col:
                    mapping['payee'] = idx
                elif 'amount' in col and mapping['amount'] == -1:
                    mapping['amount'] = idx
                elif 'fee' in col:
                    mapping['memo'] = idx
            return rows, True, mapping

        # 2. Universal Auto-Detector Fallback
        if has_header:
            # Debit & Credit columns
            for idx, col in enumerate(header):
                if any(x in col for x in ['debit amount', 'debit', 'outflow', 'withdrawal', 'dr', 'paid out', 'spent']):
                    mapping['debit'] = idx
                elif any(x in col for x in ['credit amount', 'credit', 'inflow', 'deposit', 'cr', 'paid in', 'received']):
                    mapping['credit'] = idx

            # Date column
            for idx, col in enumerate(header):
                if 'value date' in col and mapping['date'] != -1:
                    continue
                if any(x in col for x in ['transaction date', 'trans date', 'booking date', 'date', 'posted', 'time']):
                    if mapping['date'] == -1 or 'transaction' in col or 'trans' in col:
                        mapping['date'] = idx

            # Payee / Description column
            for idx, col in enumerate(header):
                if any(x in col for x in ['payee', 'merchant', 'beneficiary', 'party']):
                    mapping['payee'] = idx
                    break
                elif any(x in col for x in ['description', 'particulars', 'narrative', 'details']):
                    if mapping['payee'] == -1 or 'supplementary' not in col:
                        mapping['payee'] = idx

            # Amount column (if not separate debit/credit)
            if mapping['debit'] == -1 and mapping['credit'] == -1:
                for idx, col in enumerate(header):
                    if any(x in col for x in ['amount', 'sum', 'total', 'net']):
                        mapping['amount'] = idx
                        break

            # Category column
            for idx, col in enumerate(header):
                if any(x in col for x in ['category', 'cat', 'classification']):
                    mapping['category'] = idx
                    break

            # Memo / Reference column
            for idx, col in enumerate(header):
                if any(x in col for x in ['memo', 'notes', 'reference', 'client reference', 'additional reference', 'ref']):
                    if idx != mapping['payee'] and idx != mapping['date']:
                        mapping['memo'] = idx
        else:
            mapping.update({'date': 0, 'payee': 1, 'amount': 2, 'memo': 3 if len(rows[0]) > 3 else -1})

        return rows, has_header, mapping

    def _csv_mapping(self, auto):
        """The effective mapping: user overrides (1-based columns) win over
        the auto-detected indices (0 = use auto)."""
        mapping = dict(auto)
        overrides = {
            'date': self.csv_date_col,
            'payee': self.csv_payee_col,
            'amount': self.csv_amount_col,
            'debit': self.csv_debit_col,
            'credit': self.csv_credit_col,
            'category': self.csv_category_col,
            'memo': self.csv_memo_col,
        }
        for key, col in overrides.items():
            if col:
                mapping[key] = col - 1
        return mapping

    def _clean_bank_payee(self, raw_payee, supplementary='', profile='auto'):
        """Clean raw bank narration strings into recognizable merchant/payee names."""
        p = raw_payee.strip() if raw_payee else ''
        if not p and supplementary:
            p = supplementary.strip()

        # 1. PayNow Transfer
        if 'paynow transfer' in p.lower() and 'to:' in p.lower():
            m = re.search(r'to:\s*([^\s,]+(?:\s+[^\s,]+)*?)(?:\s+othr|\s+ref|\s+from|$)', p, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        # 2. Incoming PayNow
        if 'incoming paynow' in p.lower() and 'from:' in p.lower():
            m = re.search(r'from:\s*([^\s,]+(?:\s+[^\s,]+)*?)(?:\s+othr|\s+ref|$)', p, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        # 3. PayLah! Top-up
        if 'top-up to paylah!' in p.lower():
            m = re.search(r'top-up to paylah!\s*:\s*([^,\s]+(?:\s+[^,\s]+)*?)(?:\s+tf|\s+plpe|$)', p, re.IGNORECASE)
            if m:
                return f"DBS PayLah! ({m.group(1).strip()})"
            return "DBS PayLah! Top-up"

        # 4. IRAS Tax
        if 'iras' in p.lower():
            if 'property' in p.lower():
                return "IRAS - Property Tax"
            elif 'itx' in p.lower() or 'income' in p.lower():
                return "IRAS - Income Tax"
            return "IRAS"

        # 5. Ministry of Manpower (MOM) / Foreign Worker Levy
        if 'ministry of manpower' in p.lower() or 'fwlevy' in p.lower():
            return "Ministry of Manpower (MOM)"

        # 6. Ministry of Education (MOE)
        if 'moe' in p.lower() and 'bill' in p.lower():
            return "Ministry of Education (MOE)"

        # 7. ATM Cash Withdrawal
        if p.startswith('CSH ') and ',' in p:
            parts = p.split(',', 1)
            return f"ATM - {parts[1].strip()}"

        # 8. NETS / FlashPay / CashCard Top-up
        if p.startswith('CCT ') and ',' in p:
            parts = p.split(',', 1)
            clean_loc = re.sub(r'\s+\d{10,}$', '', parts[1].strip())
            return f"NETS/CashCard - {clean_loc}"

        # 9. GIRO / IBG Prefix removal
        p = re.sub(r'^(IBG|GRO|GIRO|ICT|TRF|WDL)\s+', '', p, flags=re.IGNORECASE).strip()
        p = re.sub(r'\s+(Bill\d+|REF:\s*\d+|OTHR\s+.*|SUPP-\d+.*)$', '', p, flags=re.IGNORECASE).strip()

        return p or supplementary or 'Bank Transaction'

    def _parse_date(self, date_str):
        if not date_str:
            return fields.Date.context_today(self)
        s = date_str.strip()
        # 1. Textual month formats (e.g. 31-Jul-26, 31-Jul-2026, 31 Jul 2026)
        for fmt in ('%d-%b-%y', '%d-%b-%Y', '%d %b %Y', '%d-%B-%Y', '%b-%d-%y', '%b-%d-%Y',
                    '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
            except ValueError:
                pass

        # 2. Digits only formats
        clean = re.sub(r"[^\d/\-\.]", "", s)
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y'):
            try:
                return datetime.strptime(clean, fmt).strftime('%Y-%m-%d')
            except ValueError:
                pass

        return fields.Date.context_today(self)

    def _parse_csv(self, content):
        rows, has_header, auto = self._detect_csv_mapping(content, profile=self.bank_profile)
        if not rows:
            return 0, 0
        mapping = self._csv_mapping(auto)
        data_rows = rows[1:] if self.csv_has_header else rows

        date_idx = mapping['date']
        payee_idx = mapping['payee']
        amt_idx = mapping['amount']
        debit_idx = mapping['debit']
        credit_idx = mapping['credit']
        cat_idx = mapping['category']
        memo_idx = mapping['memo']

        count = 0
        skipped = 0
        TxEnv = self.env['moneta.transaction']

        for row in data_rows:
            if not row or len(row) == 0:
                continue

            try:
                raw_date = row[date_idx] if 0 <= date_idx < len(row) else ''
                parsed_date = self._parse_date(raw_date)

                raw_payee = row[payee_idx].strip() if 0 <= payee_idx < len(row) else ''
                supplementary = row[5].strip() if len(row) > 5 else ''
                payee_str = self._clean_bank_payee(raw_payee, supplementary, profile=self.bank_profile)

                cat_str = row[cat_idx].strip() if 0 <= cat_idx < len(row) else ''
                memo_str = row[memo_idx].strip() if 0 <= memo_idx < len(row) else ''
                if not memo_str and raw_payee and raw_payee != payee_str:
                    memo_str = raw_payee

                amount = 0.0
                if 0 <= amt_idx < len(row) and row[amt_idx]:
                    cleaned_amt = re.sub(r"[^\d\.\-\+]", "", row[amt_idx].replace(',', ''))
                    if cleaned_amt:
                        amount = float(cleaned_amt)
                elif (0 <= debit_idx < len(row) or 0 <= credit_idx < len(row)):
                    debit_val = 0.0
                    credit_val = 0.0
                    if 0 <= debit_idx < len(row) and row[debit_idx]:
                        c_d = re.sub(r"[^\d\.]", "", row[debit_idx].replace(',', ''))
                        if c_d:
                            debit_val = float(c_d)
                    if 0 <= credit_idx < len(row) and row[credit_idx]:
                        c_c = re.sub(r"[^\d\.]", "", row[credit_idx].replace(',', ''))
                        if c_c:
                            credit_val = float(c_c)
                    amount = credit_val - debit_val

                # Deduplication check
                if self.skip_duplicates and amount != 0.0:
                    existing = TxEnv.search([
                        ('account_id', '=', self.account_id.id),
                        ('transaction_date', '=', parsed_date),
                        ('amount', '=', round(amount, 4)),
                    ], limit=1)
                    if existing:
                        skipped += 1
                        continue

                self._create_imported_transaction({
                    'date': parsed_date,
                    'payee': payee_str,
                    'category': cat_str,
                    'amount': amount,
                    'memo': memo_str
                })
                count += 1
            except Exception:
                continue

        return count, skipped

    def _parse_qif(self, content):
        lines = content.splitlines()
        count = 0
        current_tx = {}
        current_split = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            code = line[0]
            val = line[1:].strip()

            if code == 'D':
                current_tx['date'] = self._parse_date(val)
            elif code == 'T':
                try:
                    current_tx['amount'] = float(val.replace(',', ''))
                except ValueError:
                    current_tx['amount'] = 0.0
            elif code == 'N':
                current_tx['check_number'] = val
            elif code == 'C':
                if val.upper() in ('X', 'R'):
                    current_tx['state'] = 'reconciled'
                elif val.upper() in ('*', 'C'):
                    current_tx['state'] = 'cleared'
                else:
                    current_tx['state'] = 'unreconciled'
            elif code == 'P':
                current_tx['payee'] = val
            elif code == 'L':
                current_tx['category'] = val
            elif code == 'M':
                current_tx['memo'] = val
            elif code == 'S':
                if 'splits' not in current_tx:
                    current_tx['splits'] = []
                current_split = {'category': val, 'memo': '', 'amount': 0.0}
                current_tx['splits'].append(current_split)
            elif code == 'E':
                if current_split is not None:
                    current_split['memo'] = val
            elif code == '$':
                if current_split is not None:
                    try:
                        current_split['amount'] = float(val.replace(',', ''))
                    except ValueError:
                        current_split['amount'] = 0.0
            elif line == '^':
                if 'amount' in current_tx:
                    if self._maybe_apply_opening_balance(current_tx):
                        pass
                    else:
                        self._create_imported_transaction(current_tx)
                        count += 1
                current_tx = {}
                current_split = None

        return count

    def _parse_ofx(self, content):
        count = 0
        blocks = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', content, re.DOTALL | re.IGNORECASE)
        for block in blocks:
            fields_map = dict(_OFX_FIELD_RE.findall(block))
            trnamt = self._ofx_value(fields_map, 'TRNAMT')
            if trnamt is None:
                continue

            name = self._ofx_value(fields_map, 'NAME') or ''
            memo = self._ofx_value(fields_map, 'MEMO') or ''
            trntype = (self._ofx_value(fields_map, 'TRNTYPE') or '').upper()
            date_raw = self._ofx_value(fields_map, 'DTPOSTED') or ''

            try:
                amount = float(trnamt.replace(',', ''))
            except (TypeError, ValueError):
                continue

            parsed_date = self._parse_ofx_date(date_raw)
            is_transfer = trntype == 'XFER'

            self._create_imported_transaction({
                'date': parsed_date,
                'payee': name,
                'amount': amount,
                'memo': memo,
                'is_transfer': is_transfer,
            })
            count += 1
        return count

    @staticmethod
    def _ofx_value(fields_map, tag):
        for key, val in fields_map.items():
            if key.upper() == tag:
                return val.strip()
        return None

    def _parse_ofx_date(self, date_raw):
        if not date_raw:
            return fields.Date.context_today(self)
        clean = re.sub(r"[^\d]", "", date_raw)
        if len(clean) >= 8:
            try:
                dt = datetime.strptime(clean[:8], '%Y%m%d')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return fields.Date.context_today(self)

    def _maybe_apply_opening_balance(self, tx_dict):
        payee = (tx_dict.get('payee') or '').strip().lower()
        if payee != 'opening balance':
            return False
        amount = tx_dict.get('amount', 0.0) or 0.0
        date = tx_dict.get('date') or fields.Date.context_today(self)
        self.account_id.write({
            'opening_balance': amount,
            'opening_balance_date': date,
        })
        return True

    def _create_imported_transaction(self, tx_dict):
        PayeeEnv = self.env['moneta.payee']
        CategoryEnv = self.env['moneta.category']
        RuleEnv = self.env['moneta.transaction.rule']

        payee_id = False
        if tx_dict.get('payee'):
            p_name = tx_dict['payee'].strip()
            payee = PayeeEnv._resolve_by_name(p_name)
            if not payee:
                payee = PayeeEnv.create({'name': p_name})
            payee_id = payee.id

        category_id = False
        if tx_dict.get('category'):
            c_name = tx_dict['category'].strip()
            if c_name.startswith('[') and c_name.endswith(']'):
                target_acc_name = c_name[1:-1].strip()
                target_acc = self.env['moneta.account'].search([
                    ('name', '=ilike', target_acc_name),
                    ('id', '!=', self.account_id.id)
                ], limit=1)
                if target_acc:
                    tx_dict['is_transfer'] = True
                    tx_dict['transfer_account_id'] = target_acc.id
            else:
                cat = CategoryEnv.search([('name', '=ilike', c_name)], limit=1)
                if not cat:
                    cat = CategoryEnv.create({'name': c_name, 'is_income': tx_dict.get('amount', 0.0) > 0})
                category_id = cat.id
        elif payee_id and PayeeEnv.browse(payee_id).default_category_id:
            category_id = PayeeEnv.browse(payee_id).default_category_id.id

        vals = {
            'account_id': self.account_id.id,
            'transaction_date': tx_dict.get('date', fields.Date.context_today(self)),
            'check_number': tx_dict.get('check_number', False),
            'payee_id': payee_id,
            'category_id': category_id,
            'amount': tx_dict.get('amount', 0.0),
            'memo': tx_dict.get('memo', ''),
            'is_transfer': tx_dict.get('is_transfer', False),
            'transfer_account_id': tx_dict.get('transfer_account_id', False),
            'state': tx_dict.get('state', 'cleared'),
        }

        splits = tx_dict.get('splits', [])
        if splits:
            vals['is_split'] = True
            split_commands = []
            for s in splits:
                s_cat_id = False
                if s.get('category'):
                    scat = CategoryEnv.search([('name', '=ilike', s['category'].strip())], limit=1)
                    if not scat:
                        scat = CategoryEnv.create({'name': s['category'].strip(), 'is_income': False})
                    s_cat_id = scat.id
                split_commands.append((0, 0, {
                    'category_id': s_cat_id,
                    'memo': s.get('memo', ''),
                    'amount': s.get('amount', 0.0),
                }))
            vals['split_ids'] = split_commands

        tx = self.env['moneta.transaction'].create(vals)

        # Apply active automation rules if enabled
        if self.apply_rules:
            rules = RuleEnv.search([('user_id', '=', self.env.user.id), ('active', '=', True)], order='sequence asc, id asc')
            for rule in rules:
                if rule.matches_transaction(tx):
                    rule.apply_to_transaction(tx)
                    break

        return tx
