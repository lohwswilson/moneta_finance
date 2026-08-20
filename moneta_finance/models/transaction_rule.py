# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MonetaTransactionRule(models.Model):
    _name = 'moneta.transaction.rule'
    _description = 'Moneta Automated Transaction Rule'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)

    # Condition: Payee Matching
    match_payee_type = fields.Selection([
        ('contains', 'Contains (Case-Insensitive)'),
        ('exact', 'Exact Match'),
        ('starts_with', 'Starts With'),
    ], string='Payee Match Type', default='contains')
    match_payee_text = fields.Char(string='Payee Keyword')

    # Condition: Memo / Description Matching
    match_memo_type = fields.Selection([
        ('contains', 'Contains (Case-Insensitive)'),
        ('exact', 'Exact Match'),
    ], string='Memo Match Type', default='contains')
    match_memo_text = fields.Char(string='Memo Keyword')

    # Condition: Account Scope
    match_account_ids = fields.Many2many('moneta.account', string='Apply Only to Accounts')

    # Condition: Amount Range
    amount_min = fields.Float(string='Min Amount (Optional)')
    amount_max = fields.Float(string='Max Amount (Optional)')

    # Action: Target Fields to Apply
    set_category_id = fields.Many2one('moneta.category', string='Assign Category')
    set_payee_id = fields.Many2one('moneta.payee', string='Assign Standard Payee')
    set_tag_ids = fields.Many2many('moneta.tag', string='Assign Tags')
    set_state = fields.Selection([
        ('unreconciled', 'Keep Unreconciled'),
        ('cleared', 'Mark Cleared'),
        ('reconciled', 'Mark Reconciled'),
    ], string='Set Status')

    def matches_transaction(self, tx):
        """Check if a transaction matches all configured conditions."""
        self.ensure_one()
        # 1. Account filter
        if self.match_account_ids and tx.account_id not in self.match_account_ids:
            return False

        # 2. Payee filter
        if self.match_payee_text:
            p_name = (tx.payee_id.name or '').lower() if tx.payee_id else ''
            kw = self.match_payee_text.strip().lower()
            if self.match_payee_type == 'contains' and kw not in p_name:
                return False
            elif self.match_payee_type == 'exact' and kw != p_name:
                return False
            elif self.match_payee_type == 'starts_with' and not p_name.startswith(kw):
                return False

        # 3. Memo filter
        if self.match_memo_text:
            memo = (tx.memo or '').lower()
            kw = self.match_memo_text.strip().lower()
            if self.match_memo_type == 'contains' and kw not in memo:
                return False
            elif self.match_memo_type == 'exact' and kw != memo:
                return False

        # 4. Amount filters
        amt = abs(float(tx.amount or 0.0))
        if self.amount_min and amt < self.amount_min:
            return False
        if self.amount_max and amt > self.amount_max:
            return False

        return True

    def apply_to_transaction(self, tx):
        """Apply the rule actions to a single transaction."""
        self.ensure_one()
        vals = {}
        if self.set_category_id and not tx.is_split:
            vals['category_id'] = self.set_category_id.id
        if self.set_payee_id:
            vals['payee_id'] = self.set_payee_id.id
        if self.set_state:
            vals['state'] = self.set_state
        if self.set_tag_ids:
            vals['tag_ids'] = [(4, tag.id) for tag in self.set_tag_ids]
        if vals:
            tx.write(vals)

    def action_apply_retroactive(self):
        """Execute this rule across all historical transactions."""
        self.ensure_one()
        domain = [('user_id', '=', self.user_id.id)]
        if self.match_account_ids:
            domain.append(('account_id', 'in', self.match_account_ids.ids))

        txs = self.env['moneta.transaction'].search(domain)
        matched_count = 0
        for tx in txs:
            if self.matches_transaction(tx):
                self.apply_to_transaction(tx)
                matched_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rule Applied',
                'message': f"Rule '{self.name}' successfully applied to {matched_count} transaction(s).",
                'type': 'success',
                'sticky': False,
            }
        }
