# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaGoal(models.Model):
    _name = 'moneta.goal'
    _description = 'Moneta Financial Goal & Sinking Fund'
    _order = 'target_date asc, name asc'

    name = fields.Char(string='Goal Name', required=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    # Goal Financials
    target_amount = fields.Monetary(string='Target Amount', required=True, default=10000.0)
    current_amount = fields.Monetary(string='Current Saved Amount', default=0.0)
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today, required=True)
    target_date = fields.Date(string='Target Date', required=True)

    account_id = fields.Many2one('moneta.account', string='Dedicated Bank Account (Optional)')
    color = fields.Integer(string='Color Index', default=4)
    icon = fields.Char(string='Emoji / Icon', default='🎯')

    # Computed Metrics
    progress_percent = fields.Float(string='Progress (%)', compute='_compute_goal_progress', store=True, digits=(5, 1))
    remaining_amount = fields.Monetary(string='Remaining Needed', compute='_compute_goal_progress', store=True)
    months_remaining = fields.Integer(string='Months Remaining', compute='_compute_goal_progress', store=True)
    monthly_contribution_required = fields.Monetary(string='Monthly Savings Needed', compute='_compute_goal_progress', store=True)

    status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('achieved', 'Goal Achieved! 🎉'),
        ('paused', 'Paused'),
    ], string='Status', default='in_progress', compute='_compute_goal_progress', store=True)

    notes = fields.Text(string='Motivation & Notes')

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            bal = float(self.account_id.current_balance or 0.0)
            if bal > 0:
                self.current_amount = bal

    @api.depends('target_amount', 'current_amount', 'target_date')
    def _compute_goal_progress(self):
        today = fields.Date.context_today(self)
        for goal in self:
            tgt = float(goal.target_amount or 0.0)
            cur = float(goal.current_amount or 0.0)
            goal.remaining_amount = round(max(tgt - cur, 0.0), 4)

            if tgt > 0:
                goal.progress_percent = round(min((cur / tgt) * 100.0, 100.0), 1)
            else:
                goal.progress_percent = 0.0

            if cur >= tgt and tgt > 0:
                goal.status = 'achieved'
            elif goal.status != 'paused':
                goal.status = 'in_progress'

            # Calculate remaining months & required monthly savings
            if goal.target_date and goal.target_date > today:
                delta = relativedelta(goal.target_date, today)
                months = max(delta.years * 12 + delta.months + (1 if delta.days > 0 else 0), 1)
                goal.months_remaining = months
                goal.monthly_contribution_required = round(goal.remaining_amount / months, 4)
            else:
                goal.months_remaining = 0
                goal.monthly_contribution_required = goal.remaining_amount

    def action_add_funds(self):
        """Quick dialog to deposit/allocate funds towards this goal."""
        self.ensure_one()
        return {
            'name': f'Contribute to {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.goal.fund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_goal_id': self.id, 'default_action_type': 'deposit'},
        }


class MonetaGoalFundWizard(models.TransientModel):
    _name = 'moneta.goal.fund.wizard'
    _description = 'Moneta Goal Fund Allocation Wizard'

    goal_id = fields.Many2one('moneta.goal', string='Goal', required=True)
    currency_id = fields.Many2one('res.currency', related='goal_id.currency_id', readonly=True)
    action_type = fields.Selection([
        ('deposit', 'Add / Save Funds (+)'),
        ('withdraw', 'Withdraw Funds (-)'),
    ], string='Action', default='deposit', required=True)
    amount = fields.Monetary(string='Amount', required=True, default=100.0)

    def action_apply(self):
        self.ensure_one()
        amt = float(self.amount or 0.0)
        if amt <= 0:
            raise UserError("Please specify an amount greater than 0.")
        if self.action_type == 'deposit':
            self.goal_id.current_amount += amt
        else:
            self.goal_id.current_amount = max(self.goal_id.current_amount - amt, 0.0)
        return {'type': 'ir.actions.act_window_close'}
