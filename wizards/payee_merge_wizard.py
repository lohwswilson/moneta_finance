# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaPayeeMergeWizard(models.TransientModel):
    _name = 'moneta.payee.merge.wizard'
    _description = 'Merge Duplicate Payees & Create Aliases'

    primary_payee_id = fields.Many2one('moneta.payee', string='Target Primary Payee', required=True)
    duplicate_payee_ids = fields.Many2many('moneta.payee', string='Duplicate Payees to Merge', required=True)
    create_aliases = fields.Boolean(string='Add Merged Names as Search Aliases', default=True)

    @api.onchange('primary_payee_id')
    def _onchange_primary_payee_id(self):
        if self.primary_payee_id:
            # Auto-suggest duplicates with similar names
            name = self.primary_payee_id.name.strip().lower()
            dupes = self.env['moneta.payee'].search([
                ('id', '!=', self.primary_payee_id.id),
                ('name', 'ilike', name[:4] if len(name) >= 4 else name),
            ])
            self.duplicate_payee_ids = [(6, 0, dupes.ids)]

    def action_merge(self):
        self.ensure_one()
        if not self.duplicate_payee_ids:
            raise UserError("Please select at least one duplicate payee to merge.")

        if self.primary_payee_id in self.duplicate_payee_ids:
            raise UserError("Primary payee cannot be in the list of duplicates to merge.")

        dupe_ids = self.duplicate_payee_ids.ids

        # 1. Reassign transactions
        txs = self.env['moneta.transaction'].search([('payee_id', 'in', dupe_ids)])
        tx_count = len(txs)
        txs.write({'payee_id': self.primary_payee_id.id})

        # 2. Reassign recurring transactions
        scheds = self.env['moneta.recurring.transaction'].search([('payee_id', 'in', dupe_ids)])
        scheds.write({'payee_id': self.primary_payee_id.id})

        # 3. Create aliases if requested
        if self.create_aliases:
            for dupe in self.duplicate_payee_ids:
                if dupe.name and dupe.name.lower() != self.primary_payee_id.name.lower():
                    self.env['moneta.payee.alias'].create({
                        'payee_id': self.primary_payee_id.id,
                        'pattern': f"*{dupe.name}*",
                    })

        # 4. Remove / deactivate duplicates
        for dupe in self.duplicate_payee_ids:
            dupe.active = False

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Payees Merged Successfully',
                'message': f"Merged {len(dupe_ids)} duplicate(s) into '{self.primary_payee_id.name}'. Reassigned {tx_count} transaction(s).",
                'type': 'success',
                'sticky': False,
            }
        }
