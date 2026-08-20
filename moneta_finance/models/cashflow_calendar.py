# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class MonetaCashflowProjection(models.Model):
    _name = 'moneta.cashflow.projection'
    _description = 'Quicken-Style Projected Cash Flow & Financial Calendar'
    _order = 'start_date desc, id desc'

    name = fields.Char(string='Projection Title', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    account_id = fields.Many2one(
        'moneta.account', string='Account (Leave blank for All Liquid Accounts)',
        domain="[('account_type', 'in', ('checking', 'chequing', 'savings', 'cash', 'credit_card'))]"
    )
    
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today, required=True)
    forecast_days = fields.Selection([
        ('30', 'Next 30 Days (1 Month)'),
        ('60', 'Next 60 Days (2 Months)'),
        ('90', 'Next 90 Days (1 Quarter)'),
        ('180', 'Next 180 Days (Half Year)'),
        ('365', 'Next 365 Days (1 Full Year)'),
    ], string='Forecast Horizon', default='90', required=True)
    end_date = fields.Date(string='End Date', compute='_compute_end_date', store=True)

    # Key Summary Metrics
    starting_balance = fields.Monetary(string='Starting Cash Balance', compute='_compute_projections', store=True)
    lowest_projected_balance = fields.Monetary(string='Lowest Projected Balance', compute='_compute_projections', store=True)
    lowest_balance_date = fields.Date(string='Lowest Balance Date', compute='_compute_projections', store=True)
    ending_projected_balance = fields.Monetary(string='Ending Projected Balance', compute='_compute_projections', store=True)
    
    total_projected_income = fields.Monetary(string='Total Projected Inflows', compute='_compute_projections', store=True)
    total_projected_expenses = fields.Monetary(string='Total Projected Outflows', compute='_compute_projections', store=True)
    net_projected_cashflow = fields.Monetary(string='Net Cash Flow ($)', compute='_compute_projections', store=True)
    
    overdraft_days_count = fields.Integer(string='Overdraft Risk Days', compute='_compute_projections', store=True)
    has_overdraft_risk = fields.Boolean(string='Overdraft Warning', compute='_compute_projections', store=True)

    line_ids = fields.One2many('moneta.cashflow.projection.line', 'projection_id', string='Daily Projected Balances')

    @api.depends('account_id', 'forecast_days', 'start_date')
    def _compute_name(self):
        for rec in self:
            acc_label = rec.account_id.name if rec.account_id else 'All Liquid Accounts'
            rec.name = f"{acc_label} - {rec.forecast_days}d Cash Flow Forecast ({rec.start_date})"

    @api.depends('start_date', 'forecast_days')
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date and rec.forecast_days:
                days = int(rec.forecast_days)
                rec.end_date = rec.start_date + timedelta(days=days)
            else:
                rec.end_date = False

    @api.depends('account_id', 'start_date', 'forecast_days')
    def _compute_projections(self):
        for rec in self:
            if not rec.start_date or not rec.forecast_days:
                continue

            # 1. Calculate Starting Balance
            if rec.account_id:
                start_bal = float(rec.account_id.current_balance or 0.0)
            else:
                liquid_accs = self.env['moneta.account'].search([
                    ('user_id', '=', rec.user_id.id),
                    ('account_type', 'in', ('checking', 'chequing', 'savings', 'cash')),
                    ('is_closed', '=', False),
                ])
                start_bal = sum(float(a.current_balance or 0.0) for a in liquid_accs)
            
            rec.starting_balance = round(start_bal, 2)

            # 2. Gather active recurring schedules
            sched_domain = [('user_id', '=', rec.user_id.id), ('active', '=', True)]
            if rec.account_id:
                sched_domain.append(('account_id', '=', rec.account_id.id))
            else:
                sched_domain.append(('account_id.account_type', 'in', ('checking', 'chequing', 'savings', 'cash')))

            schedules = self.env['moneta.recurring.transaction'].search(sched_domain)

            num_days = int(rec.forecast_days or 90)
            cur_date = rec.start_date
            end_date = cur_date + timedelta(days=num_days)

            # Map date -> list of events
            events_by_date = {}
            for sched in schedules:
                next_d = sched.next_date
                amt = float(sched.amount or 0.0)
                freq = sched.frequency
                desc = sched.name or 'Scheduled'

                # Project occurrences within horizon
                while next_d and next_d <= end_date:
                    if next_d >= cur_date:
                        events_by_date.setdefault(next_d, []).append({
                            'name': desc,
                            'amount': amt,
                            'payee': sched.payee_id.name if sched.payee_id else '',
                            'category': sched.category_id.name if sched.category_id else '',
                        })
                    if freq == 'once':
                        break
                    next_d = sched._calculate_next_due_date(next_d, freq)
                    if sched.end_date and next_d and next_d > sched.end_date:
                        break

            # 3. Simulate day-by-day running balance
            running = start_bal
            lowest_bal = start_bal
            lowest_date = cur_date
            tot_inc = 0.0
            tot_exp = 0.0
            overdraft_count = 0

            lines_to_create = []
            for d_offset in range(num_days + 1):
                day = cur_date + timedelta(days=d_offset)
                day_events = events_by_date.get(day, [])
                
                day_inc = sum(e['amount'] for e in day_events if e['amount'] > 0)
                day_exp = sum(abs(e['amount']) for e in day_events if e['amount'] < 0)
                net_day = day_inc - day_exp

                open_bal = running
                close_bal = running + net_day
                running = close_bal

                tot_inc += day_inc
                tot_exp += day_exp

                if close_bal < lowest_bal:
                    lowest_bal = close_bal
                    lowest_date = day

                if close_bal < 0:
                    overdraft_count += 1

                event_summary = ", ".join(
                    f"{e['name']} ({'+' if e['amount'] > 0 else ''}${e['amount']:,.0f})"
                    for e in day_events
                )

                lines_to_create.append({
                    'projection_date': day,
                    'day_of_week': day.strftime('%A'),
                    'opening_balance': round(open_bal, 2),
                    'total_income': round(day_inc, 2),
                    'total_expense': round(day_exp, 2),
                    'net_change': round(net_day, 2),
                    'closing_balance': round(close_bal, 2),
                    'is_overdraft': close_bal < 0,
                    'event_summary': event_summary,
                })

            rec.lowest_projected_balance = round(lowest_bal, 2)
            rec.lowest_balance_date = lowest_date
            rec.ending_projected_balance = round(running, 2)
            rec.total_projected_income = round(tot_inc, 2)
            rec.total_projected_expenses = round(tot_exp, 2)
            rec.net_projected_cashflow = round(tot_inc - tot_exp, 2)
            rec.overdraft_days_count = overdraft_count
            rec.has_overdraft_risk = overdraft_count > 0

            # Recreate lines
            rec.line_ids.unlink()
            rec.line_ids = [(0, 0, l) for l in lines_to_create]


class MonetaCashflowProjectionLine(models.Model):
    _name = 'moneta.cashflow.projection.line'
    _description = 'Daily Projected Cash Flow Line'
    _order = 'projection_date asc, id asc'

    projection_id = fields.Many2one('moneta.cashflow.projection', string='Projection', ondelete='cascade', required=True)
    currency_id = fields.Many2one('res.currency', related='projection_id.currency_id')

    projection_date = fields.Date(string='Date', required=True, index=True)
    day_of_week = fields.Char(string='Day')
    
    opening_balance = fields.Monetary(string='Opening Balance')
    total_income = fields.Monetary(string='Inflow (+)')
    total_expense = fields.Monetary(string='Outflow (-)')
    net_change = fields.Monetary(string='Net Change')
    closing_balance = fields.Monetary(string='Projected Balance')
    
    is_overdraft = fields.Boolean(string='Overdraft Risk', default=False)
    event_summary = fields.Char(string='Scheduled Bills & Income')
