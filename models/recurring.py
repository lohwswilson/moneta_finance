# -*- coding: utf-8 -*-
from calendar import monthrange
from datetime import date, timedelta
from odoo import models, fields, api


_FREQUENCY_SELECTION = [
    ('once', 'Once'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('biweekly', 'Biweekly'),
    ('every4weeks', 'Every 4 Weeks'),
    ('semimonthly', 'Semimonthly'),
    ('monthly', 'Monthly'),
    ('every2months', 'Every 2 Months'),
    ('quarterly', 'Quarterly'),
    ('semiannual', 'Semiannual'),
    ('yearly', 'Yearly'),
]


class MonetaRecurringTransaction(models.Model):
    _name = 'moneta.recurring.transaction'
    _description = 'Moneta Scheduled / Recurring Transaction'

    name = fields.Char(string='Description / Title', required=True)
    account_id = fields.Many2one('moneta.account', string='Account', required=True)
    payee_id = fields.Many2one('moneta.payee', string='Payee')
    category_id = fields.Many2one('moneta.category', string='Category', domain="[('user_id', '=', user_id)]")

    # Base Account Currency & Amount
    amount = fields.Monetary(string='Account Amount', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Account Currency',
        related='account_id.currency_id', store=True, readonly=True,
    )

    # Multi-Currency Scheduled Entry (v1.14.0)
    entry_currency_id = fields.Many2one(
        'res.currency', string='Entry Currency',
        default=lambda self: self.env.company.currency_id, required=True,
    )
    foreign_amount = fields.Monetary(
        string='Entry Amount',
        currency_field='entry_currency_id',
    )
    exchange_rate = fields.Float(
        string='Exchange Rate',
        digits=(12, 6), default=1.0,
        help='Rate to convert entry currency to account currency (Account Amount = Entry Amount * Rate).',
    )

    memo = fields.Char(string='Generated Memo', help='Memo applied to generated transactions; defaults to the title.')

    frequency = fields.Selection(
        _FREQUENCY_SELECTION, string='Frequency',
        default='monthly', required=True,
    )
    next_date = fields.Date(string='Next Due Date', default=fields.Date.context_today, required=True)
    active = fields.Boolean(default=True)
    auto_post = fields.Boolean(string='Auto-post', default=False, help='Post automatically via the daily cron when due.')

    end_date = fields.Date(string='End Date')
    total_occurrences = fields.Integer(string='Total Occurrences', default=0, help='0 = unlimited.')
    occurrences_remaining = fields.Integer(string='Occurrences Remaining', default=0)
    last_posted_date = fields.Date(string='Last Posted Date', readonly=True)
    reminder_days_before = fields.Integer(string='Reminder Days Before', default=3)
    is_bill = fields.Boolean(string='Is Bill / Expense', compute='_compute_due_status', store=True)
    due_status = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Due Today'),
        ('due_soon', 'Due in 7 Days'),
        ('upcoming', 'Upcoming'),
    ], string='Due Status', compute='_compute_due_status')

    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True,
        index=True,
    )

    @api.depends('next_date', 'amount')
    def _compute_due_status(self):
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=7)
        for rec in self:
            rec.is_bill = (rec.amount or 0.0) < 0
            nd = rec.next_date
            if not nd:
                rec.due_status = 'upcoming'
            elif nd < today:
                rec.due_status = 'overdue'
            elif nd == today:
                rec.due_status = 'today'
            elif nd <= horizon:
                rec.due_status = 'due_soon'
            else:
                rec.due_status = 'upcoming'

    # ------------------------------------------------------------------
    # Next-due-date arithmetic (ported from Moneta common/recurrence.ts)
    # ------------------------------------------------------------------

    @staticmethod
    def _add_months(d, months):
        """Add months and clamp the day to the target month's length so that
        e.g. Jan 31 + 1 month -> Feb 28/29, not an invalid date."""
        idx = d.month - 1 + months
        year = d.year + idx // 12
        month = idx % 12 + 1
        day = min(d.day, monthrange(year, month)[1])
        return date(year, month, day)

    @api.model
    def _calculate_next_due_date(self, current, frequency):
        if not current:
            return False
        if frequency == 'once':
            return False
        if frequency == 'daily':
            return current + timedelta(days=1)
        if frequency == 'weekly':
            return current + timedelta(weeks=1)
        if frequency == 'biweekly':
            return current + timedelta(weeks=2)
        if frequency == 'every4weeks':
            return current + timedelta(weeks=4)
        if frequency == 'semimonthly':
            # Moneta SEMIMONTHLY: day <= 15 -> last day of current month;
            # otherwise -> 15th of next month.
            if current.day <= 15:
                return date(current.year, current.month, monthrange(current.year, current.month)[1])
            return self._add_months(current.replace(day=15), 1)
        if frequency == 'monthly':
            return self._add_months(current, 1)
        if frequency == 'every2months':
            return self._add_months(current, 2)
        if frequency == 'quarterly':
            return self._add_months(current, 3)
        if frequency == 'semiannual':
            return self._add_months(current, 6)
        if frequency == 'yearly':
            return self._add_months(current, 12)
        return False

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def _prepare_transaction_values(self):
        return {
            'account_id': self.account_id.id,
            'transaction_date': self.next_date,
            'payee_id': self.payee_id.id if self.payee_id else False,
            'category_id': self.category_id.id if self.category_id else False,
            'amount': self.amount,
            'memo': self.memo or f"Scheduled: {self.name}",
            'state': 'unreconciled',
            'user_id': self.user_id.id,
        }

    def post(self):
        """Generate the due transaction, record the post, advance next_date,
        and prune the schedule (deactivate at end_date / 0 occurrences;
        'once' deletes itself after posting)."""
        for sched in self:
            self.env['moneta.transaction'].create(sched._prepare_transaction_values())
            posted_date = sched.next_date
            if sched.frequency == 'once':
                sched.unlink()
                continue
            new_next = self._calculate_next_due_date(posted_date, sched.frequency)
            vals = {'next_date': new_next, 'last_posted_date': posted_date}
            if sched.total_occurrences and sched.total_occurrences > 0:
                remaining = (sched.occurrences_remaining or sched.total_occurrences) - 1
                vals['occurrences_remaining'] = max(remaining, 0)
            active = True
            if sched.end_date and new_next and new_next > sched.end_date:
                active = False
            if sched.total_occurrences and vals.get('occurrences_remaining', sched.occurrences_remaining) <= 0:
                active = False
            vals['active'] = active
            sched.write(vals)

    def skip(self):
        """Advance next_date without generating a transaction."""
        for sched in self:
            if sched.frequency == 'once':
                sched.write({'active': False})
                continue
            new_next = self._calculate_next_due_date(sched.next_date, sched.frequency)
            vals = {'next_date': new_next}
            if sched.end_date and new_next and new_next > sched.end_date:
                vals['active'] = False
            sched.write(vals)

    def action_post_now(self):
        """1-click button to enter directly into register."""
        self.ensure_one()
        self.post()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Entered in Register',
                'message': f"Posted '{self.name}' on {self.last_posted_date}.",
                'type': 'success',
                'sticky': False,
            }
        }

    def action_skip_occurrence(self):
        """1-click button to skip this occurrence."""
        self.ensure_one()
        self.skip()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Skipped',
                'message': f"Skipped occurrence for '{self.name}'. Next due: {self.next_date}.",
                'type': 'info',
                'sticky': False,
            }
        }

    def action_generate_transaction(self):
        """Manual button: post the due transaction now."""
        self.ensure_one()
        self.post()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Transaction Generated',
                'message': f"Posted a transaction for '{self.name}' on {self.next_date}.",
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _cron_auto_post(self):
        """Daily cron: post every active auto-post schedule whose next_date is
        due. Runs with elevated access so it can read every schedule, then
        switches to each schedule's owner so the generated transaction is owned
        by the right user."""
        today = fields.Date.context_today(self)
        schedules = self.sudo().search([
            ('active', '=', True),
            ('auto_post', '=', True),
            ('next_date', '<=', today),
        ])
        for sched in schedules:
            sched.with_user(sched.user_id.id or self.env.uid).post()

    @api.onchange('foreign_amount', 'entry_currency_id', 'exchange_rate', 'account_id')
    def _onchange_multi_currency(self):
        for rec in self:
            if not rec.account_id:
                continue
            acc_curr = rec.account_id.currency_id
            if rec.entry_currency_id and rec.entry_currency_id != acc_curr:
                rate = rec.exchange_rate or 1.0
                rec.amount = (rec.foreign_amount or 0.0) * rate
            elif rec.entry_currency_id and rec.entry_currency_id == acc_curr:
                rec.amount = rec.foreign_amount or rec.amount
                rec.exchange_rate = 1.0

    @api.onchange('total_occurrences')
    def _onchange_total_occurrences(self):
        if self.total_occurrences and not self.occurrences_remaining:
            self.occurrences_remaining = self.total_occurrences