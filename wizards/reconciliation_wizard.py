# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaReconciliationWizard(models.TransientModel):
    _name = 'moneta.reconciliation.wizard'
    _description = 'Moneta Bank Statement Reconciliation Wizard'

    account_id = fields.Many2one('moneta.account', string='Account to Reconcile', required=True)
    currency_id = fields.Many2one('res.currency', related='account_id.currency_id', readonly=True)

    statement_date = fields.Date(string='Statement Ending Date', default=fields.Date.context_today, required=True)
    statement_ending_balance = fields.Monetary(string='Statement Ending Balance', required=True, default=0.0)

    opening_cleared_balance = fields.Monetary(string='Cleared Opening Balance', readonly=True)
    
    cleared_payments_total = fields.Monetary(string='Cleared Payments / Decreases', compute='_compute_reconciliation_totals')
    cleared_deposits_total = fields.Monetary(string='Cleared Deposits / Increases', compute='_compute_reconciliation_totals')
    cleared_balance = fields.Monetary(string='Total Cleared Balance', compute='_compute_reconciliation_totals')
    difference = fields.Monetary(string='Difference (Target: 0.00)', compute='_compute_reconciliation_totals')

    line_ids = fields.One2many('moneta.reconciliation.wizard.line', 'wizard_id', string='Transactions to Reconcile')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_account_id = self.env.context.get('default_account_id') or self.env.context.get('active_id')
        if active_account_id and self.env.context.get('active_model') == 'moneta.account':
            account = self.env['moneta.account'].browse(active_account_id)
            res['account_id'] = account.id
            res['opening_cleared_balance'] = account.cleared_balance

            # Populate lines from unreconciled / cleared transactions up to today
            txs = self.env['moneta.transaction'].search([
                ('account_id', '=', account.id),
                ('state', 'in', ('unreconciled', 'cleared')),
            ], order='transaction_date asc, id asc')

            lines = []
            for tx in txs:
                lines.append((0, 0, {
                    'transaction_id': tx.id,
                    'is_cleared': tx.state == 'cleared',
                    'transaction_date': tx.transaction_date,
                    'check_number': tx.check_number,
                    'payee_id': tx.payee_id.id if tx.payee_id else False,
                    'memo': tx.memo,
                    'amount': tx.amount,
                    'currency_id': tx.currency_id.id if tx.currency_id else False,
                }))
            res['line_ids'] = lines
        return res

    @api.depends('statement_ending_balance', 'opening_cleared_balance', 'line_ids.is_cleared', 'line_ids.amount')
    def _compute_reconciliation_totals(self):
        for wiz in self:
            cleared_lines = wiz.line_ids.filtered(lambda l: l.is_cleared)
            payments = 0.0
            deposits = 0.0
            for line in cleared_lines:
                amt = float(line.amount or 0.0)
                if amt < 0:
                    payments += abs(amt)
                else:
                    deposits += amt
            wiz.cleared_payments_total = round(payments, 4)
            wiz.cleared_deposits_total = round(deposits, 4)
            
            # Opening balance + sum of all cleared transactions
            # (In Quicken, Cleared Balance = Opening Balance + Cleared Deposits - Cleared Payments)
            wiz.cleared_balance = round(float(wiz.account_id.opening_balance or 0.0) + (deposits - payments), 4)
            wiz.difference = round(float(wiz.statement_ending_balance or 0.0) - wiz.cleared_balance, 4)

    def action_select_all(self):
        for line in self.line_ids:
            line.is_cleared = True
        return {'type': 'ir.actions.do_nothing'}

    def action_unselect_all(self):
        for line in self.line_ids:
            line.is_cleared = False
        return {'type': 'ir.actions.do_nothing'}

    def action_reconcile_finish(self):
        self.ensure_one()
        cleared_lines = self.line_ids.filtered(lambda l: l.is_cleared)
        if not cleared_lines:
            raise UserError("No transactions have been selected to reconcile.")

        # Reconcile all selected transactions
        tx_ids = cleared_lines.mapped('transaction_id')
        tx_ids.write({
            'state': 'reconciled',
            'reconciled_date': self.statement_date or fields.Date.context_today(self),
        })

        # Recompute account balance
        self.account_id._recompute_balance()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Account Reconciled',
                'message': f"Successfully reconciled {len(tx_ids)} transactions for {self.account_id.name} through {self.statement_date}.",
                'type': 'success',
                'sticky': False,
            }
        }


class MonetaReconciliationWizardLine(models.TransientModel):
    _name = 'moneta.reconciliation.wizard.line'
    _description = 'Moneta Reconciliation Wizard Line'
    _order = 'transaction_date asc, id asc'

    wizard_id = fields.Many2one('moneta.reconciliation.wizard', string='Wizard', ondelete='cascade')
    transaction_id = fields.Many2one('moneta.transaction', string='Transaction', required=True)

    is_cleared = fields.Boolean(string='Clr', default=False)
    transaction_date = fields.Date(string='Date')
    check_number = fields.Char(string='Check #')
    payee_id = fields.Many2one('moneta.payee', string='Payee')
    memo = fields.Char(string='Memo')
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
