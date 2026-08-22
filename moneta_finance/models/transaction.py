# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# Fields whose change alters a transaction's balance contribution. Editing
# any of these requires recomputing the account delta in the write override.
_BALANCE_FIELDS = frozenset(('amount', 'state', 'transaction_date', 'account_id'))
_TRANSFER_FIELDS = frozenset(('category_id', 'is_transfer', 'transfer_account_id', 'payee_id', 'memo'))
_PROPAGATE_FIELDS = _BALANCE_FIELDS | _TRANSFER_FIELDS


class MonetaTransaction(models.Model):
    _name = 'moneta.transaction'
    _description = 'Moneta Financial Transaction'
    _order = 'transaction_date desc, amount desc, id desc'

    transaction_date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    account_id = fields.Many2one('moneta.account', string='Account', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='account_id.currency_id', store=True, readonly=True)

    check_number = fields.Char(string='Check # / Ref')
    payee_id = fields.Many2one('moneta.payee', string='Payee')
    category_id = fields.Many2one('moneta.category', string='Category', domain="['|', '|', ('user_id', '=', uid), ('user_id', '=', 1), ('is_system', '=', True)]")

    amount = fields.Monetary(string='Amount', required=True, default=0.0)
    payment_amount = fields.Monetary(string='Payment / Decrease', compute='_compute_payment_deposit', inverse='_inverse_payment_deposit')
    deposit_amount = fields.Monetary(string='Deposit / Increase', compute='_compute_payment_deposit', inverse='_inverse_payment_deposit')
    running_balance = fields.Monetary(string='Balance', compute='_compute_running_balance')
    memo = fields.Char(string='Memo / Description')

    state = fields.Selection([
        ('unreconciled', 'Unreconciled'),
        ('cleared', 'Cleared'),
        ('reconciled', 'Reconciled'),
        ('void', 'Void'),
    ], string='Status', default='unreconciled', required=True)
    reconciled_date = fields.Date(string='Reconciled Date')

    # Transfer handling. is_transfer flags a transfer; transfer_account_id is
    # set only on the originating leg. linked_transaction_id is the mutual link
    # between the two legs (ondelete set null so deleting one leg detaches the
    # other rather than cascading).
    is_transfer = fields.Boolean(string='Is Transfer', default=False)
    transfer_account_id = fields.Many2one('moneta.account', string='Transfer To/From Account')
    linked_transaction_id = fields.Many2one('moneta.transaction', string='Linked Transfer Leg', ondelete='set null')

    # Split lines. The parent carries amount = sum of splits; the split rows are
    # a separate model and are never summed into the balance (no double count).
    is_split = fields.Boolean(string='Is Split Transaction', default=False)
    split_ids = fields.One2many('moneta.transaction.split', 'transaction_id', string='Split Details')

    tag_ids = fields.Many2many('moneta.tag', string='Tags')
    receipt_attachment = fields.Binary(string='Receipt / Invoice', attachment=True)
    receipt_filename = fields.Char(string='Receipt Filename')
    attachment_count = fields.Integer(string='Attachments', compute='_compute_attachment_count')
    payee_image = fields.Image(related='payee_id.image_128', string='Payee Logo', readonly=True)
    category_icon = fields.Char(related='category_id.effective_icon', string='Category Glyph', readonly=True)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id and self.category_id.transfer_account_id:
            self.is_transfer = True
            self.transfer_account_id = self.category_id.transfer_account_id.id
        elif self.category_id and not self.category_id.is_transfer and self.is_transfer:
            self.is_transfer = False
            self.transfer_account_id = False

    @api.onchange('transfer_account_id', 'is_transfer')
    def _onchange_transfer_account(self):
        if self.is_transfer and self.transfer_account_id:
            t_cat = self.env['moneta.category'].search([('transfer_account_id', '=', self.transfer_account_id.id)], limit=1)
            if t_cat:
                self.category_id = t_cat.id
        elif not self.is_transfer and self.category_id and self.category_id.is_transfer:
            self.category_id = False

    def _compute_attachment_count(self):
        for rec in self:
            count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'moneta.transaction'),
                ('res_id', '=', rec.id),
            ])
            if rec.receipt_attachment:
                count = max(count, 1)
            rec.attachment_count = count

    def action_batch_mark_cleared(self):
        """Server action: Mark all selected transactions as Cleared."""
        self.write({'state': 'cleared'})
        return True

    def action_batch_mark_reconciled(self):
        """Server action: Mark all selected transactions as Reconciled."""
        self.write({'state': 'reconciled'})
        return True

    def action_batch_mark_unreconciled(self):
        """Server action: Mark all selected transactions as Unreconciled."""
        self.write({'state': 'unreconciled'})
        return True

    def action_batch_set_category(self):
        """Server action: Open batch category assignment wizard."""
        return {
            'name': 'Batch Assign Category',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.transaction.batch.category.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_transaction_ids': [(6, 0, self.ids)]},
        }

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'name': 'Attachments',
            'domain': [('res_model', '=', 'moneta.transaction'), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,list,form',
            'context': {'default_res_model': 'moneta.transaction', 'default_res_id': self.id},
        }

    @api.depends('amount')
    def _compute_payment_deposit(self):
        for rec in self:
            amt = rec.amount or 0.0
            if amt < 0:
                rec.payment_amount = round(abs(amt), 4)
                rec.deposit_amount = 0.0
            elif amt > 0:
                rec.deposit_amount = round(amt, 4)
                rec.payment_amount = 0.0
            else:
                rec.payment_amount = 0.0
                rec.deposit_amount = 0.0

    def _inverse_payment_deposit(self):
        for rec in self:
            if rec.payment_amount and not rec.deposit_amount:
                rec.amount = -round(abs(rec.payment_amount), 4)
            elif rec.deposit_amount and not rec.payment_amount:
                rec.amount = round(abs(rec.deposit_amount), 4)

    @api.depends('amount', 'account_id', 'transaction_date', 'state')
    def _compute_running_balance(self):
        for account in self.mapped('account_id'):
            account_txs = self.filtered(lambda t: t.account_id == account)
            if not account_txs:
                continue
            acc_id = account._origin.id if hasattr(account, '_origin') and account._origin.id else account.id
            if not acc_id or not isinstance(acc_id, int):
                running = float(account.opening_balance or 0.0)
                for tx in sorted(account_txs, key=lambda t: (t.transaction_date or fields.Date.context_today(self), -(t.amount or 0.0), getattr(t._origin, 'id', 0) or 0)):
                    if tx.state != 'void':
                        running += (tx.amount or 0.0)
                    tx.running_balance = running
                continue

            self.env.cr.execute("""
                SELECT id, 
                       (COALESCE(%s, 0) + SUM(CASE WHEN state <> 'void' THEN amount ELSE 0 END) 
                        OVER (PARTITION BY account_id ORDER BY transaction_date ASC, amount DESC, id ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))::float
                FROM moneta_transaction
                WHERE account_id = %s
            """, (float(account.opening_balance or 0.0), acc_id))
            res_map = dict(self.env.cr.fetchall())
            for tx in account_txs:
                tx_id = tx._origin.id if hasattr(tx, '_origin') and tx._origin.id else tx.id
                tx.running_balance = res_map.get(tx_id, 0.0)
        for tx in self.filtered(lambda t: not t.account_id):
            tx.running_balance = 0.0

    # ------------------------------------------------------------------
    # Balance contribution
    # ------------------------------------------------------------------

    def _balance_contribution(self):
        """Signed amount this transaction currently adds to its account's
        current_balance. Balance-affecting = state != void AND date <= today.
        Split children live in a separate model and are never counted here."""
        self.ensure_one()
        if not self.account_id or self.state == 'void':
            return 0.0
        today = fields.Date.context_today(self)
        if self.transaction_date and self.transaction_date > today:
            return 0.0
        return self.amount or 0.0

    def _cleared_contribution(self):
        """Signed amount this transaction adds to cleared_balance: state in
        (cleared, reconciled) AND date <= today."""
        self.ensure_one()
        if not self.account_id or self.state not in ('cleared', 'reconciled'):
            return 0.0
        today = fields.Date.context_today(self)
        if self.transaction_date and self.transaction_date > today:
            return 0.0
        return self.amount or 0.0

    def _snapshot_balance(self):
        return {
            'account_id': self.account_id.id,
            'current_contrib': self._balance_contribution(),
            'cleared_contrib': self._cleared_contribution(),
        }

    # ------------------------------------------------------------------
    # Transfers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_paired_transfer_vals(vals):
        """A transfer that should create a counterpart leg: is_transfer set,
        a target account given, and the target differs from the source."""
        return (
            vals.get('is_transfer')
            and vals.get('transfer_account_id')
            and vals.get('transfer_account_id') != vals.get('account_id')
        )

    def _create_transfer_counterpart(self, source):
        """Create the counterpart leg for a same-owner, same-currency transfer.
        The counterpart lives in the target account, carries the opposite sign,
        and points back at the source via linked_transaction_id; the source is
        then linked back to it. Cross-owner and cross-currency transfers are
        deferred and refused here."""
        target = self.env['moneta.account'].browse(source.transfer_account_id.id)
        source_account = source.account_id
        if not target.exists():
            raise ValidationError("Transfer target account does not exist.")
        if target.user_id != source_account.user_id:
            raise ValidationError(
                "Cross-owner transfers are not supported in this MVP."
            )
        cat_source = self.env['moneta.category'].search([('transfer_account_id', '=', source_account.id)], limit=1)

        # Calculate target amount in target account's native currency
        if target.currency_id == source_account.currency_id:
            target_amount = round(-(source.amount or 0.0), 4)
        else:
            converted = source_account.currency_id._convert(
                abs(source.amount or 0.0),
                target.currency_id,
                self.env.company,
                source.transaction_date or fields.Date.context_today(self),
            )
            target_amount = round(-converted if (source.amount or 0.0) > 0 else converted, 4)

        # Smart Match: check if an unlinked transaction already exists in the target account
        # (e.g. statements for both accounts were imported before setting the transfer category)
        min_date = source.transaction_date - timedelta(days=3)
        max_date = source.transaction_date + timedelta(days=3)
        domain = [
            ('account_id', '=', target.id),
            ('linked_transaction_id', '=', False),
            ('transaction_date', '>=', min_date),
            ('transaction_date', '<=', max_date),
        ]
        if target.currency_id == source_account.currency_id:
            domain.append(('amount', '=', target_amount))
        else:
            if target_amount > 0:
                domain.append(('amount', '>', 0))
            else:
                domain.append(('amount', '<', 0))

        existing_match = self.search(domain, order='transaction_date asc, id asc', limit=1)

        if existing_match:
            super(MonetaTransaction, existing_match).write({
                'is_transfer': True,
                'transfer_account_id': source_account.id,
                'category_id': cat_source.id if cat_source else False,
                'linked_transaction_id': source.id,
            })
            super(MonetaTransaction, source).write({'linked_transaction_id': existing_match.id})
            return existing_match, False

        counterpart = super(MonetaTransaction, self).create([{
            'account_id': target.id,
            'transaction_date': source.transaction_date,
            'payee_id': source.payee_id.id if source.payee_id else False,
            'category_id': cat_source.id if cat_source else False,
            'amount': target_amount,
            'memo': source.memo,
            'state': source.state,
            'is_transfer': True,
            'transfer_account_id': source_account.id,
            'linked_transaction_id': source.id,
            'user_id': target.user_id.id,
        }])
        super(MonetaTransaction, source).write({'linked_transaction_id': counterpart.id})
        return counterpart, True

    def _propagate_to_counterpart(self, vals, batch_ids):
        """Mirror structural edits onto the linked counterpart leg (amount
        negated, date/state/memo copied, target account moved). Uses super().write so the counterpart
        does not re-enter this override, then applies its balance delta
        manually. Skipped when the counterpart is in the same write batch
        (the user is editing both legs explicitly)."""
        counterpart = self.linked_transaction_id
        if not counterpart or counterpart.id in batch_ids:
            return
        
        # If this transaction was converted to a non-transfer, remove counterpart
        if ('is_transfer' in vals and not vals['is_transfer']) or ('category_id' in vals and not self.is_transfer):
            self.write({'linked_transaction_id': False})
            counterpart.unlink()
            return

        cp_vals = {}
        Account = self.env['moneta.account']
        
        # 1. Target Account changed (moved transfer to another destination account)
        if 'transfer_account_id' in vals or 'category_id' in vals:
            new_target_acc_id = self.transfer_account_id.id
            if new_target_acc_id and counterpart.account_id.id != new_target_acc_id:
                # Check if the new target account already has an unlinked matching transaction
                # (e.g. from an existing statement import)
                target_amount = round(-(self.amount or 0.0), 4)
                min_date = self.transaction_date - timedelta(days=3)
                max_date = self.transaction_date + timedelta(days=3)
                existing_match = self.search([
                    ('account_id', '=', new_target_acc_id),
                    ('linked_transaction_id', '=', False),
                    ('amount', '=', target_amount),
                    ('transaction_date', '>=', min_date),
                    ('transaction_date', '<=', max_date),
                ], order='transaction_date asc, id asc', limit=1)

                if existing_match:
                    cat_source = self.env['moneta.category'].search([('transfer_account_id', '=', self.account_id.id)], limit=1)
                    old_cp = counterpart
                    old_cp.write({'linked_transaction_id': False})
                    super(MonetaTransaction, self).write({'linked_transaction_id': existing_match.id})
                    super(MonetaTransaction, existing_match).write({
                        'is_transfer': True,
                        'transfer_account_id': self.account_id.id,
                        'category_id': cat_source.id if cat_source else False,
                        'linked_transaction_id': self.id,
                    })
                    old_cp.unlink()
                    return
                else:
                    cp_vals['account_id'] = new_target_acc_id
                
        # 2. Source Account changed (moved this transaction to another source account)
        if 'account_id' in vals:
            new_source_acc_id = self.account_id.id
            if new_source_acc_id and counterpart.transfer_account_id.id != new_source_acc_id:
                cp_vals['transfer_account_id'] = new_source_acc_id
                cat_source = self.env['moneta.category'].search([('transfer_account_id', '=', new_source_acc_id)], limit=1)
                if cat_source:
                    cp_vals['category_id'] = cat_source.id

        if 'amount' in vals:
            if counterpart.currency_id == self.currency_id:
                cp_vals['amount'] = round(-(self.amount or 0.0), 4)
        if 'transaction_date' in vals:
            cp_vals['transaction_date'] = self.transaction_date
        if 'state' in vals:
            if self.state == 'void' and counterpart.state != 'void':
                cp_vals['state'] = 'void'
            elif self.state != 'void' and counterpart.state == 'void':
                cp_vals['state'] = 'unreconciled'
            # Non-VOID status changes (unreconciled / cleared / reconciled) remain per-account
            # because bank statements for each account arrive and reconcile independently.
        if 'memo' in vals:
            cp_vals['memo'] = self.memo
        if 'payee_id' in vals:
            cp_vals['payee_id'] = self.payee_id.id if self.payee_id else False

        if not cp_vals:
            return

        cp_snap = counterpart._snapshot_balance()
        super(MonetaTransaction, counterpart).write(cp_vals)
        new_current = counterpart._balance_contribution()
        new_cleared = counterpart._cleared_contribution()
        if cp_snap['account_id'] != counterpart.account_id.id:
            Account._apply_balance_delta(cp_snap['account_id'], -cp_snap['current_contrib'], -cp_snap['cleared_contrib'])
            Account._apply_balance_delta(counterpart.account_id.id, new_current, new_cleared)
        else:
            Account._apply_balance_delta(
                counterpart.account_id.id,
                new_current - cp_snap['current_contrib'],
                new_cleared - cp_snap['cleared_contrib'],
            )

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        CatEnv = self.env['moneta.category']
        for vals in vals_list:
            if vals.get('category_id'):
                cat = CatEnv.browse(vals['category_id']).exists()
                if cat and cat.transfer_account_id:
                    vals['is_transfer'] = True
                    vals['transfer_account_id'] = cat.transfer_account_id.id
        # A split parent carries no category on its own line.
        for vals in vals_list:
            if vals.get('is_split'):
                vals['category_id'] = False
        primary = super().create(vals_list)
        results = []
        for rec, vals in zip(primary, vals_list):
            results.append(rec)
            if self._is_paired_transfer_vals(vals):
                counterpart, is_new = rec._create_transfer_counterpart(rec)
                if is_new:
                    results.append(counterpart)
        # Apply the balance delta for every created record (primary + counterpart).
        Account = self.env['moneta.account']
        for rec in results:
            Account._apply_balance_delta(
                rec.account_id.id,
                rec._balance_contribution(),
                rec._cleared_contribution(),
            )
        # Return only the records the caller asked to create. Including the
        # counterpart in the return would make the caller's recordset hold two
        # records (source + leg), so every follow-up write/lookup would hit
        # both -- e.g. tx.write({'amount': ...}) would set BOTH legs. The
        # counterpart remains reachable through linked_transaction_id.
        # Evaluate and apply automated transaction rules
        rules = self.env['moneta.transaction.rule'].search([('active', '=', True)], order='sequence asc, id asc')
        if rules:
            for rec in primary:
                for rule in rules:
                    if rule.matches_transaction(rec):
                        rule.apply_to_transaction(rec)
                        break

        created = self.env['moneta.transaction'].concat(*results)
        self._invalidate_budget_actuals(created._collect_category_ids())
        for account in created.mapped('account_id'):
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return primary

    def write(self, vals):
        if vals.get('is_split') and 'category_id' not in vals:
            vals = dict(vals)
            vals['category_id'] = False
        if 'category_id' in vals:
            if vals['category_id']:
                cat = self.env['moneta.category'].browse(vals['category_id']).exists()
                if cat and cat.transfer_account_id:
                    vals['is_transfer'] = True
                    vals['transfer_account_id'] = cat.transfer_account_id.id
                elif cat and not cat.transfer_account_id:
                    vals['is_transfer'] = False
                    vals['transfer_account_id'] = False
            else:
                vals['is_transfer'] = False
                vals['transfer_account_id'] = False
        needs_delta = any(f in vals for f in _PROPAGATE_FIELDS)
        batch_ids = set(self.ids)
        snapshots = {}
        if needs_delta:
            for rec in self:
                snapshots[rec.id] = rec._snapshot_balance()
        res = super().write(vals)
        if needs_delta:
            for rec in self:
                snap = snapshots.get(rec.id)
                if snap is None:
                    continue
                new_account_id = rec.account_id.id
                new_current = rec._balance_contribution()
                new_cleared = rec._cleared_contribution()
                Account = self.env['moneta.account']
                if snap['account_id'] != new_account_id:
                    Account._apply_balance_delta(snap['account_id'], -snap['current_contrib'], -snap['cleared_contrib'])
                    Account._apply_balance_delta(new_account_id, new_current, new_cleared)
                else:
                    Account._apply_balance_delta(
                        new_account_id,
                        new_current - snap['current_contrib'],
                        new_cleared - snap['cleared_contrib'],
                    )
                if rec.linked_transaction_id:
                    rec._propagate_to_counterpart(vals, batch_ids)
                elif rec.is_transfer and rec.transfer_account_id and rec.transfer_account_id != rec.account_id:
                    counterpart, is_new = rec._create_transfer_counterpart(rec)
                    if is_new:
                        Account._apply_balance_delta(
                            counterpart.account_id.id,
                            counterpart._balance_contribution(),
                            counterpart._cleared_contribution(),
                        )
        active_recs = self.exists()
        self._invalidate_budget_actuals(active_recs._collect_category_ids())
        for rec in active_recs:
            self.env['moneta.account.balance.monthly']._rebuild_for_account(rec.account_id)
        return res

    def unlink(self):
        Account = self.env['moneta.account']
        # Remove the counterpart legs of same-owner transfers along with the
        # selected records, so a transfer never leaves an orphan leg behind.
        unlink_ids = set(self.ids)
        extra = self.env['moneta.transaction']
        for rec in self:
            cp = rec.linked_transaction_id
            if cp and cp.id not in unlink_ids:
                extra |= cp
                unlink_ids.add(cp.id)
        all_recs = self | extra
        # Reverse the balance contribution of every record being removed, then
        # detach the mutual links so ondelete=set null has nothing to null.
        for rec in all_recs:
            Account._apply_balance_delta(
                rec.account_id.id,
                -rec._balance_contribution(),
                -rec._cleared_contribution(),
            )
        all_recs.write({'linked_transaction_id': False})
        cat_ids = all_recs._collect_category_ids()
        accounts = all_recs.mapped('account_id')
        res = super(MonetaTransaction, all_recs).unlink()
        self._invalidate_budget_actuals(cat_ids)
        for account in accounts:
            self.env['moneta.account.balance.monthly']._rebuild_for_account(account)
        return res

    # ------------------------------------------------------------------
    # Budget actuals invalidation
    # ------------------------------------------------------------------

    def _collect_category_ids(self):
        """Category ids whose budget actuals depend on these transactions:
        their own category plus any split-line categories."""
        ids = set(self.mapped('category_id').ids)
        for tx in self:
            ids.update(tx.split_ids.mapped('category_id').ids)
        return [cid for cid in ids if cid]

    @api.model
    def _invalidate_budget_actuals(self, category_ids):
        """Force a refresh of budget period lines for the given categories.

        The stored actual_amount compute's depends chain (M2O -> O2M -> leaf)
        registers no triggers in Odoo 18, so writes to transactions do not
        invalidate it -- only O2M membership changes do. Every transaction
        create/write/unlink therefore schedules the affected lines for
        recomputation explicitly: flush pending writes first (Odoo 18 defers
        SQL writes, so the recompute must see the truth), then add the field
        to the recompute set."""
        if not category_ids:
            return
        lines = self.env['moneta.budget.period.category'].search(
            [('category_id', 'in', category_ids)]
        )
        if not lines:
            return
        self.env.flush_all()
        self.env.add_to_compute(lines._fields['actual_amount'], lines)

    # ------------------------------------------------------------------
    # Constraints / onchanges
    # ------------------------------------------------------------------

    @api.onchange('payee_id')
    def _onchange_payee_id(self):
        if not self.payee_id:
            return
        # 1. Configured default category on Payee
        if self.payee_id.default_category_id and not self.category_id:
            self.category_id = self.payee_id.default_category_id

        # 2. Quicken QuickFill: Autocomplete from last transaction with this payee
        domain = [
            ('payee_id', '=', self.payee_id.id),
            ('user_id', '=', self.user_id.id or self.env.uid),
            ('state', '!=', 'void'),
        ]
        if self._origin.id:
            domain.append(('id', '!=', self._origin.id))

        last_tx = self.env['moneta.transaction'].search(domain, order='transaction_date desc, id desc', limit=1)
        if last_tx:
            if not self.category_id and last_tx.category_id:
                self.category_id = last_tx.category_id
            if not self.amount and last_tx.amount:
                self.amount = last_tx.amount
            if not self.memo and last_tx.memo:
                self.memo = last_tx.memo
            if last_tx.tag_ids and not self.tag_ids:
                self.tag_ids = last_tx.tag_ids

    @api.constrains('is_transfer', 'transfer_account_id', 'account_id')
    def _check_transfer_target(self):
        for rec in self:
            if rec.is_transfer and rec.transfer_account_id and rec.transfer_account_id == rec.account_id:
                raise ValidationError("A transfer's target account must differ from its source account.")

    # ------------------------------------------------------------------
    # Reconciliation actions (Moneta transaction-reconciliation.service)
    # ------------------------------------------------------------------

    def _check_reconcilable(self):
        """Rejection before write: a void transaction is terminal and cannot be
        moved to a reconciling state (doing so would silently un-void it)."""
        void = self.filtered(lambda t: t.state == 'void')
        if void:
            raise ValidationError(
                "Void transactions cannot be reconciled; un-void them first."
            )

    def action_toggle_cleared(self):
        """1-click toggle for Quicken 'Clr' column:
        unreconciled -> cleared -> reconciled -> unreconciled.
        Void transactions cannot be toggled."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state == 'void':
                continue
            if rec.state == 'unreconciled':
                rec.write({'state': 'cleared'})
            elif rec.state == 'cleared':
                rec.write({'state': 'reconciled', 'reconciled_date': rec.reconciled_date or today})
            elif rec.state == 'reconciled':
                rec.write({'state': 'unreconciled', 'reconciled_date': False})
        return True

    def action_mark_cleared(self):
        """unreconciled -> cleared (the intermediate statement-match step)."""
        self._check_reconcilable()
        self.write({'state': 'cleared'})
        return True

    def action_reconcile(self):
        """cleared -> reconciled; stamps reconciled_date when not already set."""
        self._check_reconcilable()
        today = fields.Date.context_today(self)
        for rec in self:
            rec.write({
                'state': 'reconciled',
                'reconciled_date': rec.reconciled_date or today,
            })
        return True

    def action_unreconcile(self):
        """reconciled/cleared -> unreconciled and clears reconciled_date."""
        self._check_reconcilable()
        self.write({'state': 'unreconciled', 'reconciled_date': False})
        return True

    def action_void(self):
        """Void this transaction and, for transfers, its counterpart leg
        (pair-wide). Voided rows contribute nothing to the balance, so voiding
        reverses a transaction's effect; transfer legs void together to
        preserve balance parity across both accounts (Monize v1.15.0 parity).
        """
        (self | self.mapped('linked_transaction_id')).write({'state': 'void'})
        return True

    def action_unvoid(self):
        """Reverse a void: restore this transaction (and its transfer
        counterpart) to unreconciled, re-applying its balance contribution."""
        (self | self.mapped('linked_transaction_id')).write({'state': 'unreconciled', 'reconciled_date': False})
        return True

    @api.constrains('is_split', 'amount', 'split_ids')
    def _check_split_sum(self):
        for rec in self:
            if rec.is_split and rec.split_ids:
                total = round(sum(s.amount for s in rec.split_ids), 4)
                if abs(total - round(rec.amount or 0.0, 4)) > 0.01:
                    raise ValidationError(
                        f"The sum of split lines ({total}) must match the total "
                        f"transaction amount ({round(rec.amount or 0.0, 4)})."
                    )


class MonetaTransactionSplit(models.Model):
    _name = 'moneta.transaction.split'
    _description = 'Moneta Split Transaction Detail'

    transaction_id = fields.Many2one('moneta.transaction', string='Parent Transaction', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='transaction_id.currency_id', readonly=True)

    category_id = fields.Many2one('moneta.category', string='Category', required=True, domain="['|', '|', ('user_id', '=', uid), ('user_id', '=', 1), ('is_system', '=', True)]")
    amount = fields.Monetary(string='Amount', required=True, default=0.0)
    memo = fields.Char(string='Memo')
    tag_ids = fields.Many2many('moneta.tag', string='Tags')
    receipt_attachment = fields.Binary(string='Receipt / Invoice', attachment=True)
    receipt_filename = fields.Char(string='Receipt Filename')
    attachment_count = fields.Integer(string='Attachments', compute='_compute_attachment_count')

    # Stored related owner so the per-user record rule resolves to the parent's owner.
    user_id = fields.Many2one('res.users', related='transaction_id.user_id', store=True, index=True)

    # Budget actuals must refresh when a split line changes too (the parent's
    # write override does not run for split-only edits).
    def _invalidate_budget_actuals(self):
        cat_ids = [cid for cid in set(self.mapped('category_id').ids) if cid]
        if cat_ids:
            lines = self.env['moneta.budget.period.category'].search(
                [('category_id', 'in', cat_ids)]
            )
            if lines:
                self.env.flush_all()
                self.env.add_to_compute(lines._fields['actual_amount'], lines)

    @api.model_create_multi
    def create(self, vals_list):
        CatEnv = self.env['moneta.category']
        for vals in vals_list:
            if vals.get('category_id'):
                cat = CatEnv.browse(vals['category_id']).exists()
                if cat and cat.transfer_account_id:
                    vals['is_transfer'] = True
                    vals['transfer_account_id'] = cat.transfer_account_id.id
        splits = super().create(vals_list)
        splits._invalidate_budget_actuals()
        return splits

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_budget_actuals()
        return res

    def unlink(self):
        cat_ids = [cid for cid in set(self.mapped('category_id').ids) if cid]
        res = super().unlink()
        if cat_ids:
            lines = self.env['moneta.budget.period.category'].search(
                [('category_id', 'in', cat_ids)]
            )
            if lines:
                self.env.flush_all()
                self.env.add_to_compute(lines._fields['actual_amount'], lines)
        return res