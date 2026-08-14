# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaTransactionBatchCategoryWizard(models.TransientModel):
    _name = 'moneta.transaction.batch.category.wizard'
    _description = 'Batch Assign Category & Tags to Transactions'

    transaction_ids = fields.Many2many('moneta.transaction', string='Selected Transactions', required=True)
    category_id = fields.Many2one('moneta.category', string='Assign Category', domain="[('user_id', '=', uid)]")
    tag_ids = fields.Many2many('moneta.tag', string='Assign Tags')

    def action_apply(self):
        self.ensure_one()
        vals = {}
        if self.category_id:
            vals['category_id'] = self.category_id.id
        if self.tag_ids:
            vals['tag_ids'] = [(4, t.id) for t in self.tag_ids]

        if vals:
            for tx in self.transaction_ids:
                if not tx.is_split:
                    tx.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Batch Update Applied',
                'message': f"Updated {len(self.transaction_ids)} transaction(s).",
                'type': 'success',
                'sticky': False,
            }
        }
