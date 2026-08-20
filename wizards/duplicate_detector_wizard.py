# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaDuplicateDetectorWizard(models.TransientModel):
    _name = 'moneta.duplicate.detector.wizard'
    _description = 'Duplicate Transaction Finder & Resolver Wizard'

    account_id = fields.Many2one('moneta.account', string='Filter by Account')
    date_tolerance_days = fields.Integer(string='Date Matching Tolerance (± Days)', default=2, required=True)
    match_exact_amount = fields.Boolean(string='Match Exact Amount', default=True)
    match_same_payee = fields.Boolean(string='Match Same Payee', default=False)
    
    candidate_line_ids = fields.One2many(
        'moneta.duplicate.candidate.line', 'wizard_id', string='Duplicate Candidates'
    )
    duplicate_count = fields.Integer(string='Duplicates Found', compute='_compute_duplicate_count')

    @api.depends('candidate_line_ids')
    def _compute_duplicate_count(self):
        for wiz in self:
            wiz.duplicate_count = len(wiz.candidate_line_ids)

    def action_scan_duplicates(self):
        """Scans for potential duplicate transactions based on account, amount, and date proximity."""
        self.ensure_one()
        self.candidate_line_ids.unlink()

        domain = [('state', '!=', 'void')]
        if self.account_id:
            domain.append(('account_id', '=', self.account_id.id))

        txs = self.env['moneta.transaction'].search(domain, order='account_id, amount, transaction_date asc')
        
        candidates = []
        tolerance = timedelta(days=self.date_tolerance_days or 0)
        seen_pairs = set()

        for i in range(len(txs)):
            tx1 = txs[i]
            for j in range(i + 1, min(i + 20, len(txs))):
                tx2 = txs[j]
                
                # Check account
                if tx1.account_id != tx2.account_id:
                    continue
                
                # Check amount
                if self.match_exact_amount and abs(tx1.amount - tx2.amount) > 1e-4:
                    continue

                # Check date proximity
                if abs(tx1.transaction_date - tx2.transaction_date) > tolerance:
                    continue

                # Check payee
                if self.match_same_payee and tx1.payee_id != tx2.payee_id:
                    continue

                pair_key = (min(tx1.id, tx2.id), max(tx1.id, tx2.id))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                candidates.append((0, 0, {
                    'primary_tx_id': tx1.id,
                    'duplicate_tx_id': tx2.id,
                    'account_id': tx1.account_id.id,
                    'primary_date': tx1.transaction_date,
                    'duplicate_date': tx2.transaction_date,
                    'primary_amount': tx1.amount,
                    'duplicate_amount': tx2.amount,
                    'primary_payee_id': tx1.payee_id.id if tx1.payee_id else False,
                    'duplicate_payee_id': tx2.payee_id.id if tx2.payee_id else False,
                    'primary_memo': tx1.memo,
                    'duplicate_memo': tx2.memo,
                    'selected': True,
                }))

        self.write({'candidate_line_ids': candidates})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.duplicate.detector.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_delete_selected_duplicates(self):
        """Deletes the identified duplicate transaction while keeping the primary record."""
        self.ensure_one()
        lines = self.candidate_line_ids.filtered(lambda l: l.selected)
        if not lines:
            raise UserError("No duplicate items selected.")

        dupe_txs = lines.mapped('duplicate_tx_id')
        count = len(dupe_txs)
        dupe_txs.unlink()
        lines.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Duplicates Removed',
                'message': f"Successfully removed {count} duplicate transaction(s).",
                'type': 'success',
                'sticky': False,
            }
        }

    def action_merge_selected_duplicates(self):
        """Merges memos, tags, and notes from duplicate transactions into primary records, then deletes duplicates."""
        self.ensure_one()
        lines = self.candidate_line_ids.filtered(lambda l: l.selected)
        if not lines:
            raise UserError("No duplicate items selected.")

        merged_count = 0
        for line in lines:
            primary = line.primary_tx_id
            dupe = line.duplicate_tx_id
            if primary and dupe and primary.exists() and dupe.exists():
                # Merge memo if different
                if dupe.memo and dupe.memo not in (primary.memo or ''):
                    new_memo = f"{primary.memo or ''} | {dupe.memo}".strip(' |')
                    primary.write({'memo': new_memo})
                
                # Merge tags
                if dupe.tag_ids:
                    combined_tags = primary.tag_ids | dupe.tag_ids
                    primary.write({'tag_ids': [(6, 0, combined_tags.ids)]})

                dupe.unlink()
                merged_count += 1

        lines.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Duplicates Merged',
                'message': f"Successfully merged {merged_count} duplicate transaction pair(s).",
                'type': 'success',
                'sticky': False,
            }
        }


class MonetaDuplicateCandidateLine(models.TransientModel):
    _name = 'moneta.duplicate.candidate.line'
    _description = 'Duplicate Candidate Pair'

    wizard_id = fields.Many2one('moneta.duplicate.detector.wizard', string='Wizard', ondelete='cascade')
    selected = fields.Boolean(string='Resolve', default=True)

    account_id = fields.Many2one('moneta.account', string='Account')
    primary_tx_id = fields.Many2one('moneta.transaction', string='Original Record')
    duplicate_tx_id = fields.Many2one('moneta.transaction', string='Duplicate Record')

    primary_date = fields.Date(string='Original Date')
    duplicate_date = fields.Date(string='Duplicate Date')

    primary_amount = fields.Monetary(string='Original Amount', currency_field='currency_id')
    duplicate_amount = fields.Monetary(string='Duplicate Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='account_id.currency_id')

    primary_payee_id = fields.Many2one('moneta.payee', string='Original Payee')
    duplicate_payee_id = fields.Many2one('moneta.payee', string='Duplicate Payee')

    primary_memo = fields.Char(string='Original Memo')
    duplicate_memo = fields.Char(string='Duplicate Memo')
