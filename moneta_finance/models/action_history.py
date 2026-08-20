# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaActionHistory(models.Model):
    _name = 'moneta.action.history'
    _description = 'Moneta Action History & Mutation Log'
    _order = 'create_date desc, id desc'

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )
    description = fields.Char(string='Action Description', required=True)
    entity_type = fields.Selection([
        ('transaction', 'Transaction'),
        ('account', 'Account'),
        ('payee', 'Payee'),
        ('category', 'Category'),
        ('rule', 'Transaction Rule'),
        ('import', 'Bank Statement Import'),
        ('batch', 'Batch Operation'),
    ], string='Entity Type', required=True, default='transaction')
    entity_id = fields.Integer(string='Target Record ID')
    action = fields.Selection([
        ('create', 'Create Record'),
        ('update', 'Update / Edit'),
        ('delete', 'Delete Record'),
        ('batch_import', 'Batch Import'),
        ('batch_categorize', 'Batch Categorization'),
        ('rule_apply', 'Rule Execution'),
    ], string='Action Type', required=True)

    before_data = fields.Text(string='Before Snapshot (JSON)')
    after_data = fields.Text(string='After Snapshot (JSON)')
    record_count = fields.Integer(string='Affected Records', default=1)
    is_undone = fields.Boolean(string='Undone / Reverted', default=False, index=True)
    undone_at = fields.Datetime(string='Undone At')

    @api.model
    def log_action(self, description, entity_type, action, entity_id=False, before_data=None, after_data=None, record_count=1):
        """Convenience helper to record an undoable user mutation."""
        return self.create({
            'user_id': self.env.user.id,
            'description': description,
            'entity_type': entity_type,
            'action': action,
            'entity_id': entity_id or 0,
            'before_data': json.dumps(before_data) if before_data is not None else False,
            'after_data': json.dumps(after_data) if after_data is not None else False,
            'record_count': record_count,
            'is_undone': False,
        })

    def action_undo(self):
        """Reverts the recorded mutation."""
        self.ensure_one()
        if self.is_undone:
            raise UserError("This action has already been undone.")

        before = json.loads(self.before_data) if self.before_data else {}
        after = json.loads(self.after_data) if self.after_data else {}

        model_name = f"moneta.{self.entity_type}"
        if self.entity_type in ('import', 'batch'):
            model_name = 'moneta.transaction'

        if self.action in ('create', 'batch_import'):
            # Revert creation: delete created records
            target_ids = after.get('ids') or ([self.entity_id] if self.entity_id else [])
            if model_name in self.env and target_ids:
                records = self.env[model_name].browse(target_ids).exists()
                if records:
                    records.unlink()

        elif self.action in ('update', 'batch_categorize', 'rule_apply'):
            # Revert updates: restore previous field values
            records_data = before.get('records', [])
            if model_name in self.env:
                for rec_data in records_data:
                    rec_id = rec_data.get('id')
                    vals = {k: v for k, v in rec_data.items() if k != 'id'}
                    rec = self.env[model_name].browse(rec_id).exists()
                    if rec and vals:
                        rec.write(vals)

        elif self.action == 'delete':
            # Revert deletion: re-create records
            records_data = before.get('records', [])
            if model_name in self.env:
                for vals in records_data:
                    clean_vals = {k: v for k, v in vals.items() if k != 'id'}
                    self.env[model_name].create(clean_vals)

        self.write({
            'is_undone': True,
            'undone_at': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Action Undone',
                'message': f"Successfully reverted: {self.description}",
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def action_undo_last(self):
        """Finds and reverts the most recent undoable action for current user."""
        last_action = self.search([
            ('user_id', '=', self.env.user.id),
            ('is_undone', '=', False),
        ], order='create_date desc, id desc', limit=1)

        if not last_action:
            raise UserError("No recent actions available to undo.")

        return last_action.action_undo()
