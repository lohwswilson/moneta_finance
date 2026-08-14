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
    _description = 'Moneta Financial File Import Wizard (QIF / OFX / CSV)'

    account_id = fields.Many2one('moneta.account', string='Target Account', required=True)
    file_type = fields.Selection([
        ('csv', 'CSV File'),
        ('qif', 'QIF (Quicken / MS Money)'),
        ('ofx', 'OFX / QFX (Open Financial Exchange)')
    ], string='File Type', default='csv', required=True)

    file_data = fields.Binary(string='Upload File', required=True)
    file_name = fields.Char(string='File Name')

    imported_count = fields.Integer(string='Imported Transactions Count', readonly=True)

    # CSV column mapping (editable step: auto-detect with override). Columns
    # are 1-based; 0 means "auto-detect" at import time.
    csv_has_header = fields.Boolean(string='CSV Has Header Row', default=True)
    csv_date_col = fields.Integer(string='Date Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_payee_col = fields.Integer(string='Payee Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_amount_col = fields.Integer(string='Amount Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_debit_col = fields.Integer(string='Debit Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_credit_col = fields.Integer(string='Credit Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_category_col = fields.Integer(string='Category Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_memo_col = fields.Integer(string='Memo Column', default=0, help='1-based column number; 0 = auto-detect')
    csv_column_count = fields.Integer(string='Detected Columns', readonly=True)
    csv_preview = fields.Text(string='File Preview', readonly=True)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )

    def action_detect_csv(self):
        """Parse the uploaded CSV, auto-detect the header row and column
        mapping, and fill the mapping fields for the user to adjust."""
        self.ensure_one()
        if not self.file_data:
            raise UserError("Upload a CSV file first, then detect the columns.")
        content = base64.b64decode(self.file_data).decode('utf-8-sig', errors='ignore')
        rows, has_header, mapping = self._detect_csv_mapping(content)
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
            count = self._parse_csv(content)
        elif self.file_type == 'qif':
            count = self._parse_qif(content)
        elif self.file_type == 'ofx':
            count = self._parse_ofx(content)
        else:
            raise UserError("Unsupported file type.")

        self.imported_count = count
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Completed',
                'message': f"Successfully imported {count} transactions into {self.account_id.name}.",
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _detect_csv_mapping(self, content):
        """Return (rows, has_header, mapping) for a CSV file. The mapping maps
        'date'/'payee'/'amount'/'debit'/'credit'/'category'/'memo' to 0-based
        column indices (or -1 when the column is absent)."""
        reader = csv.reader(io.StringIO(content))
        rows = [r for r in reader if r]
        mapping = {'date': -1, 'payee': -1, 'amount': -1, 'debit': -1, 'credit': -1, 'category': -1, 'memo': -1}
        if not rows:
            return rows, False, mapping
        header = [c.lower().strip() for c in rows[0]]
        has_header = any(
            k in ' '.join(header)
            for k in ['date', 'payee', 'description', 'amount', 'debit', 'credit', 'category']
        )
        if has_header:
            for idx, col in enumerate(header):
                if any(x in col for x in ['date', 'time', 'posted']):
                    mapping['date'] = idx
                elif any(x in col for x in ['payee', 'description', 'merchant', 'name', 'details']):
                    mapping['payee'] = idx
                elif any(x in col for x in ['amount', 'sum', 'total', 'val']):
                    mapping['amount'] = idx
                elif any(x in col for x in ['debit', 'outflow', 'withdraw']):
                    mapping['debit'] = idx
                elif any(x in col for x in ['credit', 'inflow', 'deposit']):
                    mapping['credit'] = idx
                elif any(x in col for x in ['category', 'cat']):
                    mapping['category'] = idx
                elif any(x in col for x in ['memo', 'notes', 'reference']):
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

    def _parse_csv(self, content):
        rows, has_header, auto = self._detect_csv_mapping(content)
        if not rows:
            return 0
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
        for row in data_rows:
            if not row or len(row) == 0:
                continue

            try:
                raw_date = row[date_idx] if 0 <= date_idx < len(row) else ''
                parsed_date = self._parse_date(raw_date)

                payee_str = row[payee_idx] if 0 <= payee_idx < len(row) else ''
                cat_str = row[cat_idx] if 0 <= cat_idx < len(row) else ''
                memo_str = row[memo_idx] if 0 <= memo_idx < len(row) else ''

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

        return count

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
                        pass  # opening-balance row does not create a transaction
                    else:
                        self._create_imported_transaction(current_tx)
                        count += 1
                current_tx = {}
                current_split = None

        return count

    def _parse_ofx(self, content):
        """Parse OFX/QFX SGML. OFX is not valid XML (tags are often unclosed),
        so we extract each <STMTTRN> block by regex and pull field values with a
        tag-value regex. The TRNAMT sign already carries direction (debit
        negative, credit positive), matching Moneta's signed-amount convention."""
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
            # XFER rows are flagged as transfers but not auto-paired: the OFX
            # file does not name the counterpart account, so pairing is left to
            # the user after import. is_transfer without transfer_account_id
            # is a flagged-but-unpaired leg (see transaction.create override).
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
        """QIF convention: a row whose payee reads 'Opening Balance' seeds the
        target account's opening balance instead of creating a transaction."""
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

    def _parse_date(self, date_str):
        if not date_str:
            return fields.Date.context_today(self)
        clean = re.sub(r"[^\d/\-\.]", "", date_str.strip())
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y'):
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return fields.Date.context_today(self)

    def _create_imported_transaction(self, tx_dict):
        PayeeEnv = self.env['moneta.payee']
        CategoryEnv = self.env['moneta.category']

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
            # Check for Quicken transfer notation [Account Name]
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
                    cat = CategoryEnv.create({'name': c_name, 'is_income': False})
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

        return self.env['moneta.transaction'].create(vals)
