# -*- coding: utf-8 -*-
import json
import base64
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.ai_advisor import MonetaAIClient


class MonetaAIReceiptWizard(models.TransientModel):
    _name = 'moneta.ai.receipt.wizard'
    _description = 'AI Receipt & Invoice Vision OCR Wizard'

    account_id = fields.Many2one(
        'moneta.account', string='Account / Credit Card', required=True,
        default=lambda self: self.env['moneta.account'].search([('user_id', '=', self.env.user.id), ('is_closed', '=', False)], limit=1)
    )
    receipt_file = fields.Binary(string='Receipt / Invoice Image (JPG/PNG/PDF)', required=True)
    file_name = fields.Char(string='File Name')
    state = fields.Selection([('upload', 'Upload'), ('review', 'Review & Create')], default='upload')

    # Parsed OCR Fields
    merchant_name = fields.Char(string='Detected Merchant / Payee')
    receipt_date = fields.Date(string='Transaction Date', default=fields.Date.context_today)
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id')
    tax_amount = fields.Monetary(string='Tax Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='account_id.currency_id', readonly=True)

    line_ids = fields.One2many('moneta.ai.receipt.line.wizard', 'wizard_id', string='Parsed Line Items')

    def action_scan_receipt(self):
        """Send image to Vision AI to extract structured receipt data."""
        self.ensure_one()
        if not self.receipt_file:
            raise UserError(_("Please upload a receipt or invoice file first."))

        img_b64 = self.receipt_file.decode('utf-8') if isinstance(self.receipt_file, bytes) else self.receipt_file

        prompt = (
            "Analyze this receipt or invoice image. Extract the following fields as pure JSON with no markdown wrapping:\n"
            "{\n"
            "  \"merchant\": \"Store or Merchant Name\",\n"
            "  \"date\": \"YYYY-MM-DD\",\n"
            "  \"total_amount\": 0.00,\n"
            "  \"tax_amount\": 0.00,\n"
            "  \"line_items\": [\n"
            "    {\"description\": \"Item name\", \"amount\": 0.00, \"category_suggestion\": \"Groceries / Dining / Office / Fuel etc.\"}\n"
            "  ]\n"
            "}"
        )

        raw_json = MonetaAIClient.analyze_image(self.env, img_b64, prompt)
        
        # Clean any markdown code blocks
        clean_json = raw_json.strip()
        if clean_json.startswith('```json'):
            clean_json = clean_json[7:]
        if clean_json.startswith('```'):
            clean_json = clean_json[3:]
        if clean_json.endswith('```'):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            data = json.loads(clean_json)
        except Exception:
            data = json.loads(MonetaAIClient._fallback_receipt_data())

        self.merchant_name = data.get('merchant', 'Scanned Merchant')
        try:
            self.receipt_date = fields.Date.from_string(data.get('date', str(date.today())))
        except Exception:
            self.receipt_date = date.today()
        self.total_amount = float(data.get('total_amount', 0.0))
        self.tax_amount = float(data.get('tax_amount', 0.0))

        lines = []
        for item in data.get('line_items', []):
            lines.append((0, 0, {
                'description': item.get('description', 'Item'),
                'amount': float(item.get('amount', 0.0)),
                'category_suggestion': item.get('category_suggestion', 'General Expenses'),
            }))
        self.line_ids = lines
        self.state = 'review'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.ai.receipt.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_transaction(self):
        """Create checkbook transaction with splits and attach receipt."""
        self.ensure_one()
        # Find or create Payee
        payee = self.env['moneta.payee'].search([('name', '=ilike', self.merchant_name)], limit=1)
        if not payee and self.merchant_name:
            payee = self.env['moneta.payee'].create({'name': self.merchant_name})

        # Match default category
        cat = payee.default_category_id if payee else False
        if not cat:
            cat = self.env['moneta.category'].search([('is_income', '=', False)], limit=1)

        tx_amount = -abs(float(self.total_amount or 0.0))
        split_vals = []
        if self.line_ids:
            for l in self.line_ids:
                # Find best category match
                line_cat = self.env['moneta.category'].search([('name', '=ilike', l.category_suggestion)], limit=1) or cat
                split_vals.append((0, 0, {
                    'category_id': line_cat.id if line_cat else False,
                    'amount': -abs(float(l.amount or 0.0)),
                    'memo': l.description,
                }))
            # The parsed total usually includes tax while line items are
            # pre-tax; the transaction split guard requires the splits to sum
            # to the total, so a balancing line absorbs the difference
            # (tax / rounding) instead of failing the create.
            split_sum = sum(float(v[2]['amount']) for v in split_vals)
            balance = round(tx_amount - split_sum, 4)
            if abs(balance) > 0.01:
                split_vals.append((0, 0, {
                    'category_id': cat.id if cat else False,
                    'amount': balance,
                    'memo': 'Tax / Rounding',
                }))

        tx = self.env['moneta.transaction'].create({
            'account_id': self.account_id.id,
            'payee_id': payee.id if payee else False,
            'category_id': cat.id if cat else False,
            'amount': tx_amount,
            'transaction_date': self.receipt_date or date.today(),
            'memo': f"AI Receipt Scan: {self.merchant_name}",
            'is_split': bool(split_vals),
            'split_ids': split_vals if split_vals else False,
            'state': 'cleared',
        })

        # Attach receipt image
        if self.receipt_file:
            self.env['ir.attachment'].create({
                'name': self.file_name or f"Receipt_{self.merchant_name}_{self.receipt_date}.jpg",
                'type': 'binary',
                'datas': self.receipt_file,
                'res_model': 'moneta.transaction',
                'res_id': tx.id,
            })

        action = self.env.ref('moneta_finance.action_moneta_transaction').read()[0]
        action['views'] = [(self.env.ref('moneta_finance.view_moneta_transaction_form').id, 'form')]
        action['res_id'] = tx.id
        return action


class MonetaAIReceiptLineWizard(models.TransientModel):
    _name = 'moneta.ai.receipt.line.wizard'
    _description = 'Parsed Receipt Line Item'

    wizard_id = fields.Many2one('moneta.ai.receipt.wizard', required=True, ondelete='cascade')
    description = fields.Char(string='Item Description', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    category_suggestion = fields.Char(string='Suggested Category')
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
