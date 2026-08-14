# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaAccount(models.Model):
    _name = 'moneta.account'
    _description = 'Moneta Financial Account'
    _order = 'is_favourite desc, name'

    name = fields.Char(string='Account Name', required=True)
    account_type = fields.Selection([
        ('chequing', 'Chequing'),
        ('savings', 'Savings'),
        ('credit_card', 'Credit Card'),
        ('loan', 'Loan'),
        ('mortgage', 'Mortgage'),
        ('loc', 'Line of Credit'),
        ('brokerage', 'Brokerage / Investment'),
        ('asset', 'Asset'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ], string='Account Type', default='chequing', required=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id, required=True,
    )

    # Balances are stored fields maintained by the three-layer model
    # (atomic delta -> recompute -> daily cron). They are NOT computed fields:
    # a stored compute would re-sum on every write and lose the atomic-delta
    # guarantee that the project contract requires.
    current_balance = fields.Monetary(string='Current Balance', store=True, readonly=True, default=0.0)
    cleared_balance = fields.Monetary(string='Cleared Balance', store=True, readonly=True, default=0.0)

    # Opening balance seeds current_balance/cleared_balance on create and is the
    # base of every recompute.
    opening_balance = fields.Monetary(string='Opening Balance', default=0.0)
    opening_balance_date = fields.Date(string='Opening Balance Date', default=fields.Date.context_today)

    credit_limit = fields.Monetary(string='Credit Limit', default=0.0)
    interest_rate = fields.Float(string='Annual Interest Rate (%)', digits=(5, 2), default=0.0)

    # Billing cycle parameters
    billing_cycle_day = fields.Integer(string='Statement Closing Day', help='Day of month when statement closes (1-31)')
    payment_due_day = fields.Integer(string='Payment Due Day', help='Day of month when payment is due (1-31)')

    account_number = fields.Char(string='Account Number / Mask')
    # Linked institution record (Phase 1); institution_name remains as a
    # free-text fallback for accounts that predate an institution record.
    institution_id = fields.Many2one('moneta.institution', string='Institution')
    institution_name = fields.Char(string='Financial Institution')
    is_favourite = fields.Boolean(string='Favourite', default=False)
    is_closed = fields.Boolean(string='Closed', default=False)
    closed_date = fields.Date(string='Closed Date')
    notes = fields.Text(string='Notes')

    # Net-worth controls (consumed in Phase 3; stored now so the field exists).
    exclude_from_net_worth = fields.Boolean(string='Exclude from Net Worth', default=False)
    # FX fee on cross-currency transfers, stored but not consumed this MVP.
    fx_fee_percent = fields.Float(string='FX Fee (%)', digits=(5, 2), default=0.0)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )
    transaction_ids = fields.One2many('moneta.transaction', 'account_id', string='Transactions')

    # Joint Accounts & Multi-User Sharing (v1.14.0)
    share_ids = fields.One2many('moneta.account.share', 'account_id', string='Shared Access Grants')
    shared_user_ids = fields.Many2many(
        'res.users',
        'moneta_account_shared_users_rel',
        'account_id',
        'user_id',
        string='Shared With',
        compute='_compute_shared_users',
        store=True,
    )
    is_shared = fields.Boolean(string='Is Shared', compute='_compute_shared_users', store=True)
    shared_count = fields.Integer(string='Shared Users Count', compute='_compute_shared_users')

    @api.depends('share_ids', 'share_ids.user_id')
    def _compute_shared_users(self):
        for acc in self:
            users = acc.share_ids.mapped('user_id')
            acc.shared_user_ids = [(6, 0, users.ids)]
            acc.is_shared = bool(users)
            acc.shared_count = len(users)

    # ------------------------------------------------------------------
    # Three-layer balance model
    # ------------------------------------------------------------------

    @api.model
    def _apply_balance_delta(self, account_id, current_delta, cleared_delta):
        """Atomically adjust an account's balances by signed deltas.

        Parameterized SQL (never interpolation) -- the project contract calls
        out exactly this form: UPDATE accounts SET current_balance =
        current_balance + $1. ROUND to 4dp preserves the decimal(20,4) money
        precision. A zero delta is a no-op.
        """
        if not account_id:
            return
        if round(current_delta or 0.0, 4) == 0.0 and round(cleared_delta or 0.0, 4) == 0.0:
            return
        self.env.cr.execute(
            "UPDATE moneta_account "
            "SET current_balance = ROUND(COALESCE(current_balance,0) + %s, 4), "
            "    cleared_balance = ROUND(COALESCE(cleared_balance,0) + %s, 4) "
            "WHERE id = %s",
            (float(current_delta or 0.0), float(cleared_delta or 0.0), account_id),
        )
        # The UPDATE bypasses the ORM cache; invalidate so the next read of this
        # account sees the new balance instead of a stale cached value.
        self.env['moneta.account'].browse(account_id).invalidate_recordset(
            ['current_balance', 'cleared_balance']
        )

    def _recompute_balance(self):
        """Full recompute from authoritative state: opening_balance + sum of
        balance-affecting transactions (state != void, date <= today). The
        cleared variant restricts to cleared|reconciled. Used to fix drift, on
        opening_balance change, and by the daily cron to roll future-dated
        transactions in once their date arrives."""
        for account in self:
            today = fields.Date.context_today(self)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(amount), 0)::float FROM moneta_transaction "
                "WHERE account_id = %s AND state <> 'void' AND transaction_date <= %s",
                (account.id, today),
            )
            current = float(account.opening_balance or 0.0) + float(self.env.cr.fetchone()[0] or 0.0)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(amount), 0)::float FROM moneta_transaction "
                "WHERE account_id = %s AND state IN ('cleared','reconciled') AND transaction_date <= %s",
                (account.id, today),
            )
            cleared = float(account.opening_balance or 0.0) + float(self.env.cr.fetchone()[0] or 0.0)
            self.env.cr.execute(
                "UPDATE moneta_account SET current_balance = %s, cleared_balance = %s WHERE id = %s",
                (round(current, 4), round(cleared, 4), account.id),
            )
        self.invalidate_recordset(['current_balance', 'cleared_balance'])

    @api.model
    def _cron_roll_in_balances(self):
        """Daily cron: recompute every active account so future-dated
        transactions that have now become due (date <= today) are rolled into
        the balance. A full recompute is cheap for personal-finance volumes and
        is the authoritative correction for any drift."""
        accounts = self.search([('is_closed', '=', False)])
        accounts._recompute_balance()

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        for account in accounts:
            # Seed balances from the opening balance (treated as cleared).
            seed = round(float(account.opening_balance or 0.0), 4)
            self.env.cr.execute(
                "UPDATE moneta_account SET current_balance = %s, cleared_balance = %s WHERE id = %s",
                (seed, seed, account.id),
            )
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        accounts.invalidate_recordset(['current_balance', 'cleared_balance'])
        return accounts

    def write(self, vals):
        # Capture the old opening balance before writing so we can decide
        # whether a recompute is needed.
        opening_changed = 'opening_balance' in vals
        res = super().write(vals)
        if opening_changed:
            # Opening balance changed -> authoritative recompute is simplest
            # and correct (the delta path does not own the opening base).
            self._recompute_balance()
            for account in self:
                self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return res

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_view_transactions(self):
        self.ensure_one()
        return {
            'name': f'Transactions - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.transaction',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def action_import_file(self):
        self.ensure_one()
        return {
            'name': f'Import File - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_account_id': self.id},
        }

    def action_recompute_balance(self):
        self._recompute_balance()
        return True

    def unlink(self):
        # Rejection before write (the project contract): an account that still
        # holds transactions or investment transactions cannot be deleted -- the
        # user should close it instead. Without this guard the ondelete on
        # moneta.transaction.account_id / moneta.investment.transaction.account_id
        # would cascade-delete every referencing row, which is silent data loss.
        # Faithful to Moneta's accounts.service.delete (refuses on
        # transactionCount / investmentTransactionCount).
        for account in self:
            tx_count = self.env['moneta.transaction'].search_count(
                [('account_id', '=', account.id)]
            )
            if tx_count:
                raise ValidationError(
                    f"Cannot delete account with {tx_count} transaction(s). "
                    "Close the account instead."
                )
            inv_count = self.env['moneta.investment.transaction'].search_count(
                [('account_id', '=', account.id)]
            )
            if inv_count:
                raise ValidationError(
                    f"Cannot delete account with {inv_count} investment "
                    "transaction(s). Close the account instead."
                )
        return super().unlink()