# -*- coding: utf-8 -*-
import base64
import io
import csv
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaExportWizard(models.TransientModel):
    _name = 'moneta.export.wizard'
    _description = 'Moneta Account Checkbook Register Export Wizard'

    account_ids = fields.Many2many('moneta.account', string='Accounts to Export', required=True)
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    export_format = fields.Selection([
        ('csv', 'CSV (Comma Delimited Spreadsheet)'),
        ('qif', 'QIF (Quicken Interchange Format)'),
    ], string='Export Format', default='csv', required=True)

    state = fields.Selection([
        ('choose', 'Choose Options'),
        ('get', 'Download File'),
    ], default='choose')

    file_data = fields.Binary(string='Exported File', readonly=True)
    file_name = fields.Char(string='Filename', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('active_model') == 'moneta.account' and self._context.get('active_ids'):
            res['account_ids'] = [(6, 0, self._context.get('active_ids'))]
        elif not res.get('account_ids'):
            accs = self.env['moneta.account'].search([('is_closed', '=', False)])
            res['account_ids'] = [(6, 0, accs.ids)]
        return res

    def action_export(self):
        self.ensure_one()
        if not self.account_ids:
            raise UserError("Please select at least one account to export.")

        domain = [('account_id', 'in', self.account_ids.ids)]
        if self.date_from:
            domain.append(('transaction_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('transaction_date', '<=', self.date_to))

        transactions = self.env['moneta.transaction'].search(domain, order='transaction_date asc, id asc')

        if self.export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['Date', 'Account', 'Payee', 'Category', 'Memo', 'Amount', 'Currency', 'Status'])

            for tx in transactions:
                writer.writerow([
                    tx.transaction_date.strftime('%Y-%m-%d') if tx.transaction_date else '',
                    tx.account_id.name if tx.account_id else '',
                    tx.payee_id.name if tx.payee_id else '',
                    tx.category_id.name if tx.category_id else '',
                    tx.memo or '',
                    f"{tx.amount:.2f}",
                    tx.currency_id.name if tx.currency_id else '',
                    tx.state or 'unreconciled',
                ])

            file_content = output.getvalue().encode('utf-8')
            filename = f"moneta_export_{fields.Date.today().strftime('%Y%m%d')}.csv"

        else: # QIF format
            qif_lines = ["!Type:Bank"]
            for tx in transactions:
                dt_str = tx.transaction_date.strftime('%m/%d/%Y') if tx.transaction_date else ''
                qif_lines.append(f"D{dt_str}")
                qif_lines.append(f"T{tx.amount:.2f}")
                if tx.payee_id:
                    qif_lines.append(f"P{tx.payee_id.name}")
                if tx.category_id:
                    qif_lines.append(f"L{tx.category_id.name}")
                if tx.memo:
                    qif_lines.append(f"M{tx.memo}")
                if tx.state in ('cleared', 'reconciled'):
                    qif_lines.append(f"C{ 'X' if tx.state == 'reconciled' else '*' }")
                qif_lines.append("^")

            file_content = "\n".join(qif_lines).encode('utf-8')
            filename = f"moneta_export_{fields.Date.today().strftime('%Y%m%d')}.qif"

        self.write({
            'state': 'get',
            'file_data': base64.b64encode(file_content),
            'file_name': filename,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
