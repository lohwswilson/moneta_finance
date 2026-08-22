from datetime import timedelta
from dateutil.relativedelta import relativedelta
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MonetaAccount(models.Model):
    _name = 'moneta.account'
    _description = 'Moneta Account'
    _order = 'sequence, is_favourite desc, name'

    sequence = fields.Integer(string='Sequence', default=10, index=True)
    name = fields.Char(string='Account Name', required=True)
    account_type = fields.Selection([
        ('checking', 'Checking'),
        ('chequing', 'Checking'),
        ('savings', 'Savings'),
        ('credit_card', 'Credit Card'),
        ('loan', 'Loan'),
        ('mortgage', 'Mortgage'),
        ('loc', 'Line of Credit'),
        ('brokerage', 'Brokerage / Investment'),
        ('asset', 'Asset'),
        ('cash', 'Cash'),
        ('cpf_oa', 'Singapore CPF Ordinary Account (OA)'),
        ('cpf_sa', 'Singapore CPF Special Account (SA)'),
        ('cpf_ma', 'Singapore CPF MediSave Account (MA)'),
        ('cpf_ra', 'Singapore CPF Retirement Account (RA)'),
        ('srs', 'Singapore Supplementary Retirement Scheme (SRS)'),
        ('other', 'Other'),
    ], string='Account Type', default='checking', required=True)

    account_group = fields.Selection([
        ('cash', 'Cash & Banking'),
        ('investment', 'Investments & Stocks'),
        ('credit', 'Credit Cards & Credit Lines'),
        ('loan', 'Loans & Mortgages'),
        ('regional', 'Regional & Retirement (CPF/SRS/EPF)'),
        ('other', 'Other Assets & Tangibles'),
    ], string='Account Group', compute='_compute_account_group', store=True, index=True)

    @api.depends('account_type')
    def _compute_account_group(self):
        for acc in self:
            t = acc.account_type
            if t in ('checking', 'chequing', 'savings', 'cash'):
                acc.account_group = 'cash'
            elif t in ('brokerage', 'retirement', 'crypto'):
                acc.account_group = 'investment'
            elif t in ('credit_card', 'loc'):
                acc.account_group = 'credit'
            elif t in ('loan', 'mortgage'):
                acc.account_group = 'loan'
            elif t in ('cpf_oa', 'cpf_sa', 'cpf_ma', 'cpf_ra', 'srs'):
                acc.account_group = 'regional'
            else:
                acc.account_group = 'other'

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
    forecast_balance_30d = fields.Monetary(string='Projected (30d)', compute='_compute_forecast_and_statement_cycle')
    forecast_balance_60d = fields.Monetary(string='Projected (60d)', compute='_compute_forecast_and_statement_cycle')
    forecast_balance_90d = fields.Monetary(string='Projected (90d)', compute='_compute_forecast_and_statement_cycle')
    next_statement_date = fields.Date(string='Next Statement Date', compute='_compute_forecast_and_statement_cycle')
    next_payment_due_date = fields.Date(string='Next Due Date', compute='_compute_forecast_and_statement_cycle')
    current_cycle_spent = fields.Monetary(string='Current Cycle Spending', compute='_compute_forecast_and_statement_cycle')
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
    # Brokerage & Investment Portfolio Integration
    holding_ids = fields.One2many('moneta.holding', 'account_id', string='Securities & Holdings')
    investment_transaction_ids = fields.One2many('moneta.investment.transaction', 'account_id', string='Investment Trades')
    total_portfolio_market_value = fields.Monetary(string='Stock Market Value', compute='_compute_brokerage_totals')
    total_portfolio_cost_basis = fields.Monetary(string='Stock Cost Basis', compute='_compute_brokerage_totals')
    total_portfolio_gain = fields.Monetary(string='Stock Gain/Loss', compute='_compute_brokerage_totals')
    total_portfolio_gain_percent = fields.Float(string='Stock Gain (%)', compute='_compute_brokerage_totals', digits=(5, 2))
    holding_count = fields.Integer(string='Holdings Count', compute='_compute_brokerage_totals')
    trade_count = fields.Integer(string='Trades Count', compute='_compute_brokerage_totals')

    @api.depends('holding_ids.market_value', 'holding_ids.cost_basis', 'investment_transaction_ids')
    def _compute_brokerage_totals(self):
        for acc in self:
            holdings = acc.holding_ids
            trades = acc.investment_transaction_ids
            mv = sum(float(h.market_value or 0.0) for h in holdings)
            cb = sum(float(h.cost_basis or 0.0) for h in holdings)
            acc.total_portfolio_market_value = mv
            acc.total_portfolio_cost_basis = cb
            acc.total_portfolio_gain = mv - cb
            acc.total_portfolio_gain_percent = ((mv - cb) / cb * 100.0) if cb > 0 else 0.0
            acc.holding_count = len(holdings)
            acc.trade_count = len(trades)

    def action_view_holdings(self):
        self.ensure_one()
        return {
            'name': f'Holdings - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.holding',
            'view_mode': 'list,form,graph',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def action_view_trades(self):
        self.ensure_one()
        return {
            'name': f'Investment Trades - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.investment.transaction',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def action_new_trade(self):
        self.ensure_one()
        return {
            'name': f'New Trade - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.investment.transaction',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_account_id': self.id},
        }

    # Loan & Mortgage Scenario Integration (v1.15.0)
    loan_scenario_ids = fields.One2many('moneta.loan.scenario', 'account_id', string='Loan Scenarios')
    loan_scenario_id = fields.Many2one('moneta.loan.scenario', string='Active Loan Scenario', compute='_compute_loan_metrics')
    loan_monthly_payment = fields.Monetary(string='Monthly Payment (P&I)', compute='_compute_loan_metrics')
    loan_payoff_date = fields.Date(string='Estimated Payoff Date', compute='_compute_loan_metrics')
    loan_remaining_interest = fields.Monetary(string='Remaining Total Interest', compute='_compute_loan_metrics')

    def _compute_loan_metrics(self):
        for acc in self:
            scenario = self.env['moneta.loan.scenario'].search([('account_id', '=', acc.id)], limit=1)
            if scenario:
                acc.loan_scenario_id = scenario.id
                acc.loan_monthly_payment = scenario.monthly_payment or 0.0
                acc.loan_payoff_date = scenario.actual_payoff_date or scenario.original_payoff_date
                acc.loan_remaining_interest = scenario.total_interest_actual or scenario.total_interest_original or 0.0
            else:
                acc.loan_scenario_id = False
                acc.loan_monthly_payment = 0.0
                acc.loan_payoff_date = False
                acc.loan_remaining_interest = 0.0

    def action_view_loan_scenario(self):
        self.ensure_one()
        scenario = self.env['moneta.loan.scenario'].search([('account_id', '=', self.id)], limit=1)
        if scenario:
            return {
                'name': f'Loan Scenario - {self.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'moneta.loan.scenario',
                'res_id': scenario.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'name': f'New Loan Scenario - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.loan.scenario',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_name': f'{self.name} Amortization',
                'default_account_id': self.id,
                'default_principal_amount': abs(float(self.current_balance or 0.0)) or 100000.0,
                'default_annual_interest_rate': self.interest_rate or 5.0,
            },
        }

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
    shared_count = fields.Integer(string='Shared Users Count', compute='_compute_shared_count')

    @api.depends('current_balance', 'billing_cycle_day', 'payment_due_day', 'account_type')
    def _compute_forecast_and_statement_cycle(self):
        today = fields.Date.context_today(self)
        for acc in self:
            cur_bal = float(acc.current_balance or 0.0)
            d30 = today + timedelta(days=30)
            d60 = today + timedelta(days=60)
            d90 = today + timedelta(days=90)
            
            scheds = self.env['moneta.recurring.transaction'].search([
                ('account_id', '=', acc.id),
                ('active', '=', True),
                ('next_date', '>=', today),
            ])
            delta_30 = sum(float(s.amount or 0.0) for s in scheds if s.next_date <= d30)
            delta_60 = sum(float(s.amount or 0.0) for s in scheds if s.next_date <= d60)
            delta_90 = sum(float(s.amount or 0.0) for s in scheds if s.next_date <= d90)
            
            acc.forecast_balance_30d = round(cur_bal + delta_30, 4)
            acc.forecast_balance_60d = round(cur_bal + delta_60, 4)
            acc.forecast_balance_90d = round(cur_bal + delta_90, 4)
            
            if acc.account_type == 'credit_card' and acc.billing_cycle_day:
                c_day = max(min(int(acc.billing_cycle_day), 28), 1)
                due_day = max(min(int(acc.payment_due_day or 15), 28), 1)
                if today.day <= c_day:
                    acc.next_statement_date = today.replace(day=c_day)
                    cycle_start = (today.replace(day=1) - relativedelta(months=1)).replace(day=c_day)
                else:
                    acc.next_statement_date = (today.replace(day=1) + relativedelta(months=1)).replace(day=c_day)
                    cycle_start = today.replace(day=c_day)
                
                acc.next_payment_due_date = (acc.next_statement_date.replace(day=1) + relativedelta(months=1)).replace(day=due_day)
                txs = self.env['moneta.transaction'].search([
                    ('account_id', '=', acc.id),
                    ('transaction_date', '>=', cycle_start),
                    ('amount', '<', 0),
                    ('state', '!=', 'void'),
                ])
                acc.current_cycle_spent = round(abs(sum(float(t.amount or 0.0) for t in txs)), 4)
            else:
                acc.next_statement_date = False
                acc.next_payment_due_date = False
                acc.current_cycle_spent = 0.0

    @api.depends('share_ids', 'share_ids.user_id')
    def _compute_shared_users(self):
        # Stored fields only; shared_count is non-stored and lives in its own
        # method (Odoo 18 warns when one compute mixes stored and non-stored).
        for acc in self:
            users = acc.share_ids.mapped('user_id')
            acc.shared_user_ids = [(6, 0, users.ids)]
            acc.is_shared = bool(users)

    @api.depends('share_ids', 'share_ids.user_id')
    def _compute_shared_count(self):
        for acc in self:
            acc.shared_count = len(acc.shared_user_ids)

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
        if 'moneta.property' in self.env:
            props = self.env['moneta.property'].search([('mortgage_account_id', '=', account_id)])
            if props:
                props._compute_equity()

    def _recompute_balance(self):
        """Full recompute from authoritative state: opening_balance + sum of
        balance-affecting transactions (state != void, date <= today). The
        cleared variant restricts to cleared|reconciled. Used to fix drift, on
        opening_balance change, and by the daily cron to roll future-dated
        transactions in once their date arrives."""
        for account in self:
            acc_id = account._origin.id if hasattr(account, '_origin') and account._origin.id else account.id
            if not acc_id or not isinstance(acc_id, int):
                continue
            today = fields.Date.context_today(self)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(amount), 0)::float FROM moneta_transaction "
                "WHERE account_id = %s AND state <> 'void' AND transaction_date <= %s",
                (acc_id, today),
            )
            row = self.env.cr.fetchone()
            current = float(account.opening_balance or 0.0) + float((row and row[0]) or 0.0)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(amount), 0)::float FROM moneta_transaction "
                "WHERE account_id = %s AND state IN ('cleared','reconciled') AND transaction_date <= %s",
                (acc_id, today),
            )
            row_c = self.env.cr.fetchone()
            cleared = float(account.opening_balance or 0.0) + float((row_c and row_c[0]) or 0.0)
            self.env.cr.execute(
                "UPDATE moneta_account SET current_balance = %s, cleared_balance = %s WHERE id = %s",
                (round(current, 4), round(cleared, 4), acc_id),
            )
        self.invalidate_recordset(['current_balance', 'cleared_balance'])
        if 'moneta.property' in self.env:
            props = self.env['moneta.property'].search([('mortgage_account_id', 'in', self.ids)])
            if props:
                props._compute_equity()

    @api.model
    def _cron_roll_in_balances(self):
        """Daily cron: recompute every active account so future-dated
        transactions that have now become due (date <= today) are rolled into
        the balance. A full recompute is cheap for personal-finance volumes and
        is the authoritative correction for any drift."""
        accounts = self.search([('is_closed', '=', False)])
        accounts._recompute_balance()

    # ------------------------------------------------------------------
    def _sync_transfer_category(self):
        """Create or update a Quicken/MS Money style transfer category [Account Name] for this account."""
        Category = self.env['moneta.category']
        for account in self:
            cat = Category.search([('transfer_account_id', '=', account.id)], limit=1)
            cat_name = f"[{account.name}]"
            user_to_assign = (hasattr(account, 'user_id') and account.user_id.id) or (self.env.uid if self.env.uid != 1 else 2)
            if cat:
                cat_vals = {}
                if cat.name != cat_name:
                    cat_vals['name'] = cat_name
                    cat_vals['icon'] = '🔁'
                if cat.user_id.id != user_to_assign:
                    cat_vals['user_id'] = user_to_assign
                if cat_vals:
                    cat.write(cat_vals)
            else:
                Category.create({
                    'name': cat_name,
                    'icon': '🔁',
                    'transfer_account_id': account.id,
                    'is_income': False,
                    'category_type': 'transfer',
                    'user_id': user_to_assign,
                })

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
        accounts._sync_transfer_category()
        accounts.invalidate_recordset(['current_balance', 'cleared_balance'])
        return accounts

    def write(self, vals):
        # Capture the old opening balance before writing so we can decide
        # whether a recompute is needed.
        opening_changed = 'opening_balance' in vals
        res = super().write(vals)
        if 'name' in vals:
            self._sync_transfer_category()
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

    def action_reconcile_statement(self):
        self.ensure_one()
        return {
            'name': f'Reconcile Statement - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.reconciliation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_account_id': self.id, 'active_id': self.id, 'active_model': 'moneta.account'},
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