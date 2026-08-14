# -*- coding: utf-8 -*-
import calendar
from odoo import models, fields, api


class MonetaBudget(models.Model):
    _name = 'moneta.budget'
    _description = 'Moneta Category Budget'
    _order = 'name'

    name = fields.Char(string='Budget Name', required=True)
    description = fields.Text(string='Description')

    # Faithful subset of Moneta's Budget entity. MVP consumes monthly/fixed;
    # the other enum values are stored but unused (annual/pay-period budgets
    # and non-fixed strategies are deferred).
    budget_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
        ('pay_period', 'Pay Period'),
    ], string='Budget Type', default='monthly', required=True)
    strategy = fields.Selection([
        ('fixed', 'Fixed'),
        ('rollover', 'Rollover'),
        ('zero_based', 'Zero Based'),
        ('fifty_thirty_twenty', '50/30/20'),
    ], string='Strategy', default='fixed', required=True)

    # Stored but not consumed this MVP (income-linked budgeting is deferred).
    base_income = fields.Monetary(string='Base Income')
    income_linked = fields.Boolean(string='Income Linked', default=False)
    config = fields.Json(string='Configuration', default=dict)

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id, required=True,
    )
    active = fields.Boolean(default=True)

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    category_ids = fields.One2many('moneta.budget.category', 'budget_id', string='Budget Categories')
    period_ids = fields.One2many('moneta.budget.period', 'budget_id', string='Periods')

    @api.model_create_multi
    def create(self, vals_list):
        budgets = super().create(vals_list)
        for budget in budgets:
            # The open period for the current month mirrors the budget lines
            # (inline lines from a form save are already present here).
            self.env['moneta.budget.period']._create_period_for_budget(budget)
        return budgets

    def action_close_current_period(self):
        """Header button: close the open period now (snapshot rollover, create
        the next month's open period)."""
        for budget in self:
            open_period = self.env['moneta.budget.period'].search([
                ('budget_id', '=', budget.id),
                ('status', '=', 'open'),
            ], limit=1)
            if open_period:
                open_period._close_period()
        return True

    def _sync_open_period(self):
        """Reconcile this budget's open period with its category lines: rebuild
        the period's lines from the budget lines, preserving the rollover_in
        seeded at close time. Called whenever the budget's lines change so the
        open period always mirrors them; closed periods stay snapshots."""
        Period = self.env['moneta.budget.period']
        period = Period.search([
            ('budget_id', '=', self.id),
            ('status', '=', 'open'),
        ], limit=1)
        if not period:
            return
        rollover = {
            pc.budget_category_id.id: pc.rollover_in
            for pc in period.period_category_ids
        }
        period.period_category_ids.unlink()
        period.write({
            # Keep total_budgeted in step with the rebuilt lines (Moneta:
            # total_budgeted = sum of non-income budget category amounts).
            'total_budgeted': round(sum(
                round(float(bc.amount or 0.0), 4)
                for bc in self.category_ids if not bc.is_income
            ), 4),
            'period_category_ids': [
                (0, 0, {
                    'budget_category_id': bc.id,
                    'category_id': bc.category_id.id,
                    'budgeted_amount': bc.amount,
                    'rollover_in': round(float(rollover.get(bc.id, 0.0)), 4),
                })
                for bc in self.category_ids
            ],
        })


class MonetaBudgetCategory(models.Model):
    _name = 'moneta.budget.category'
    _description = 'Moneta Budget Category Line'
    _order = 'sort_order, id'

    budget_id = fields.Many2one('moneta.budget', string='Budget', required=True, ondelete='cascade')
    # Category-based lines only this MVP; transfer budget categories are
    # deferred, so the category is required.
    category_id = fields.Many2one('moneta.category', string='Category', required=True, domain="[('user_id', '=', user_id)]")
    amount = fields.Monetary(string='Planned Amount', required=True)
    is_income = fields.Boolean(string='Is Income', default=False)
    category_group = fields.Selection([
        ('need', 'Need'),
        ('want', 'Want'),
        ('saving', 'Saving'),
    ], string='Category Group')
    rollover_type = fields.Selection([
        ('none', 'None'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Rollover', default='none', required=True)
    alert_warn_percent = fields.Integer(string='Warn At (%)', default=80)
    alert_critical_percent = fields.Integer(string='Critical At (%)', default=95)
    notes = fields.Text(string='Notes')
    sort_order = fields.Integer(string='Sort Order', default=0)

    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id', store=True, readonly=True)
    # Stored related owner so the per-user record rule resolves to the budget owner.
    user_id = fields.Many2one('res.users', related='budget_id.user_id', store=True, index=True)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        # Convenience: picking a category defaults is_income to the category's.
        if self.category_id:
            self.is_income = self.category_id.is_income

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line.budget_id._sync_open_period()
        return lines

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            line.budget_id._sync_open_period()
        return res

    def unlink(self):
        budgets = self.mapped('budget_id')
        res = super().unlink()
        for budget in budgets:
            budget._sync_open_period()
        return res


class MonetaBudgetPeriod(models.Model):
    _name = 'moneta.budget.period'
    _description = 'Moneta Budget Period'
    _order = 'period_start desc, id desc'

    budget_id = fields.Many2one('moneta.budget', string='Budget', required=True, ondelete='cascade')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    status = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open', required=True)

    # Snapshot at creation (Moneta createPeriodForBudget); actuals stay live.
    total_budgeted = fields.Monetary(string='Total Budgeted')
    actual_income = fields.Monetary(string='Actual Income', compute='_compute_actual_totals')
    actual_expenses = fields.Monetary(string='Actual Expenses', compute='_compute_actual_totals')

    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id', store=True, readonly=True)
    user_id = fields.Many2one('res.users', related='budget_id.user_id', store=True, index=True)

    period_category_ids = fields.One2many('moneta.budget.period.category', 'budget_period_id', string='Period Categories')

    @api.depends('period_category_ids.actual_amount', 'period_category_ids.budget_category_id.is_income')
    def _compute_actual_totals(self):
        """Live income/expense totals across the period's lines: expenses are
        counted from non-income lines, income from income lines (Moneta
        closePeriod accumulation)."""
        for period in self:
            income = 0.0
            expenses = 0.0
            for pc in period.period_category_ids:
                if pc.budget_category_id.is_income:
                    income += pc.actual_amount or 0.0
                else:
                    expenses += pc.actual_amount or 0.0
            period.actual_income = round(income, 4)
            period.actual_expenses = round(expenses, 4)

    @api.model
    def _create_period_for_budget(self, budget, rollover_map=None):
        """Create the open period for the current calendar month, one period
        category per budget category. total_budgeted = sum of non-income lines;
        each line carries budgeted_amount and the close-time rollover_in
        (Moneta createPeriodForBudget + getCurrentMonthPeriodDates)."""
        today = fields.Date.context_today(self)
        period_start = today.replace(day=1)
        period_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        rollover_map = rollover_map or {}
        total_budgeted = sum(
            round(float(bc.amount or 0.0), 4) for bc in budget.category_ids if not bc.is_income
        )
        return self.create({
            'budget_id': budget.id,
            'period_start': period_start,
            'period_end': period_end,
            'total_budgeted': round(total_budgeted, 4),
            'period_category_ids': [
                (0, 0, {
                    'budget_category_id': bc.id,
                    'category_id': bc.category_id.id,
                    'budgeted_amount': bc.amount,
                    'rollover_in': round(float(rollover_map.get(bc.id, 0.0)), 4),
                })
                for bc in budget.category_ids
            ],
        })

    def action_close_period(self):
        """Form-button wrapper: Odoo 18 forbids calling private methods from
        buttons, so the button routes through this public action."""
        self._close_period()
        return True

    def _close_period(self):
        """Close the period: snapshot each line's live actual into rollover_out
        (rollover_type != none only), mark closed, then create the next open
        period seeded with rollover_in. One ORM transaction; periods already
        closed are skipped (rejection-before-write)."""
        for period in self:
            if period.status != 'open':
                continue
            rollover_map = {}
            for pc in period.period_category_ids:
                actual = pc.actual_amount or 0.0
                pc.rollover_out = self._compute_rollover(pc, actual)
                if pc.rollover_out > 0:
                    rollover_map[pc.budget_category_id.id] = pc.rollover_out
            period.status = 'closed'
            self._create_period_for_budget(period.budget_id, rollover_map)
        return True

    @api.model
    def _compute_rollover(self, period_category, actual_amount):
        """Moneta computeRollover: unused = effective_budget - actual; 0 when
        unused <= 0 or rollover_type is none; rounded to 4dp. (rollover_cap
        clamping is deferred -- the MVP's rollover is uncapped.)"""
        bc = period_category.budget_category_id
        if not bc or bc.rollover_type == 'none':
            return 0.0
        unused = round(float(period_category.effective_budget or 0.0) - float(actual_amount or 0.0), 4)
        if unused <= 0:
            return 0.0
        return round(unused, 4)

    @api.model
    def _cron_close_expired_periods(self):
        """Daily cron: close every open period whose period_end has passed
        (creating the next month's open period with rollover), and ensure each
        active budget has a current open period. Runs under sudo so the cron
        can touch every user's budgets; ownership flows through the stored
        related user_id on periods and lines."""
        today = fields.Date.context_today(self)
        Period = self.sudo()
        for budget in self.env['moneta.budget'].sudo().search([('active', '=', True)]):
            expired = Period.search([
                ('budget_id', '=', budget.id),
                ('status', '=', 'open'),
                ('period_end', '<', today),
            ])
            for period in expired:
                period._close_period()
            if not Period.search_count([('budget_id', '=', budget.id), ('status', '=', 'open')]):
                Period._create_period_for_budget(budget)


class MonetaBudgetPeriodCategory(models.Model):
    _name = 'moneta.budget.period.category'
    _description = 'Moneta Budget Period Category Line'

    budget_period_id = fields.Many2one('moneta.budget.period', string='Budget Period', required=True, ondelete='cascade')
    budget_category_id = fields.Many2one('moneta.budget.category', string='Budget Category', required=True)
    # Snapshot of the budgeted category at period creation (Moneta stores it too).
    category_id = fields.Many2one('moneta.category', string='Category')

    budgeted_amount = fields.Monetary(string='Budgeted Amount', required=True)
    rollover_in = fields.Monetary(string='Rollover In', default=0.0)
    effective_budget = fields.Monetary(string='Effective Budget', compute='_compute_effective_budget')
    # Stored compute: the depends chain through category_id.transaction_ids /
    # split_ids makes Odoo recompute this whenever a transaction or split on
    # the category changes, so the value is always current (no stale cache).
    actual_amount = fields.Monetary(string='Actual Amount', compute='_compute_actual_amount', store=True)
    rollover_out = fields.Monetary(string='Rollover Out', default=0.0)

    alert_level = fields.Selection([
        ('none', 'On Track'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('over_budget', 'Over Budget'),
    ], string='Alert', compute='_compute_alert_level')

    spent_percent = fields.Float(string='% Spent', compute='_compute_budget_progress', digits=(5, 2))
    remaining_amount = fields.Monetary(string='Remaining', compute='_compute_budget_progress')

    currency_id = fields.Many2one('res.currency', related='budget_period_id.budget_id.currency_id', store=True, readonly=True)
    user_id = fields.Many2one('res.users', related='budget_period_id.budget_id.user_id', store=True, index=True)

    @api.depends('budgeted_amount', 'rollover_in')
    def _compute_effective_budget(self):
        # Moneta: effective_budget = budgeted + rollover_in.
        for pc in self:
            pc.effective_budget = round(float(pc.budgeted_amount or 0.0) + float(pc.rollover_in or 0.0), 4)

    @api.depends('category_id.transaction_ids.amount',
                 'category_id.transaction_ids.state',
                 'category_id.transaction_ids.transaction_date',
                 'category_id.transaction_ids.is_split',
                 'category_id.split_ids.amount',
                 'category_id.split_ids.transaction_id.state',
                 'category_id.split_ids.transaction_id.transaction_date',
                 'budget_period_id.period_start',
                 'budget_period_id.period_end',
                 'budget_category_id.is_income')
    def _compute_actual_amount(self):
        """Actual for the line (stored, recomputed on transaction/split writes):
        signed sum of the category's direct transactions (is_split=false) plus
        its split lines, within the period and not void. Expense lines negate
        and clamp refunds to 0; income lines keep the positive sum clamped at 0
        (Moneta resolveCategorySpent / computePeriodActuals)."""
        for pc in self:
            if not pc.category_id:
                pc.actual_amount = 0.0
                continue
            period = pc.budget_period_id
            if not (period.period_start and period.period_end):
                pc.actual_amount = 0.0
                continue
            self.env.cr.execute(
                "SELECT COALESCE(SUM(amount), 0)::float FROM moneta_transaction "
                "WHERE category_id = %s AND is_split = false AND state <> 'void' "
                "  AND transaction_date >= %s AND transaction_date <= %s",
                (pc.category_id.id, period.period_start, period.period_end),
            )
            total = float(self.env.cr.fetchone()[0] or 0.0)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(s.amount), 0)::float "
                "FROM moneta_transaction_split s "
                "JOIN moneta_transaction t ON s.transaction_id = t.id "
                "WHERE s.category_id = %s AND t.state <> 'void' "
                "  AND t.transaction_date >= %s AND t.transaction_date <= %s",
                (pc.category_id.id, period.period_start, period.period_end),
            )
            total += float(self.env.cr.fetchone()[0] or 0.0)
            if pc.budget_category_id.is_income:
                pc.actual_amount = round(max(total, 0.0), 4)
            else:
                pc.actual_amount = round(max(-total, 0.0), 4)

    @api.depends('effective_budget', 'actual_amount')
    def _compute_budget_progress(self):
        for pc in self:
            eff = float(pc.effective_budget or 0.0)
            act = float(pc.actual_amount or 0.0)
            pc.remaining_amount = round(eff - act, 4)
            if eff > 0:
                pc.spent_percent = round((act / eff) * 100.0, 2)
            else:
                pc.spent_percent = 0.0

    @api.depends('effective_budget', 'actual_amount',
                 'budget_category_id.alert_warn_percent', 'budget_category_id.alert_critical_percent')
    def _compute_alert_level(self):
        """Three alert types only (Moneta budget-alert subset): threshold
        warning, threshold critical, and over budget. Over budget wins over the
        thresholds."""
        for pc in self:
            effective = pc.effective_budget or 0.0
            actual = pc.actual_amount or 0.0
            if effective <= 0:
                pc.alert_level = 'none'
                continue
            warn = float(pc.budget_category_id.alert_warn_percent or 80) / 100.0
            critical = float(pc.budget_category_id.alert_critical_percent or 95) / 100.0
            if actual > effective:
                pc.alert_level = 'over_budget'
            elif actual >= critical * effective:
                pc.alert_level = 'critical'
            elif actual >= warn * effective:
                pc.alert_level = 'warning'
            else:
                pc.alert_level = 'none'