# -*- coding: utf-8 -*-
import json
from odoo import models
from .ai_client import MonetaAIClient


class MonetaTransaction(models.Model):
    _inherit = 'moneta.transaction'

    def action_ai_enrich(self):
        """Use AI to clean raw merchant strings and assign categories & tags."""
        categories = self.env['moneta.category'].search([('user_id', '=', self.env.user.id)])
        cat_names = [c.name for c in categories]

        for tx in self:
            raw_text = tx.memo or (tx.payee_id.name if tx.payee_id else '')
            if not raw_text:
                continue

            system_prompt = (
                "You are a financial transaction enrichment AI. "
                "Given a raw bank descriptor or merchant memo, extract the clean merchant/payee name, "
                f"choose the best matching category from this available list: {cat_names}, and suggest 1-2 lowercase tags. "
                "Return pure JSON format with keys: 'clean_merchant', 'category', 'tags'."
            )
            resp = MonetaAIClient.generate_text(self.env, system_prompt, raw_text)

            clean_json = resp.strip()
            if clean_json.startswith('```json'):
                clean_json = clean_json[7:]
            if clean_json.startswith('```'):
                clean_json = clean_json[3:]
            if clean_json.endswith('```'):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            try:
                data = json.loads(clean_json)
                merchant = data.get('clean_merchant')
                cat_name = data.get('category')

                vals = {}
                if merchant:
                    payee = self.env['moneta.payee'].search([('name', '=ilike', merchant)], limit=1)
                    if not payee:
                        payee = self.env['moneta.payee'].create({'name': merchant})
                    vals['payee_id'] = payee.id

                if cat_name:
                    category = self.env['moneta.category'].search([('name', '=ilike', cat_name), ('user_id', '=', self.env.user.id)], limit=1)
                    if category:
                        vals['category_id'] = category.id

                if vals:
                    tx.write(vals)
            except Exception:
                pass
        return True
