# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api


class MonetaInsight(models.TransientModel):
    _name = 'moneta.insight'
    _description = 'Moneta Smart Financial Insight'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Insight Title', required=True)
    sequence = fields.Integer(string='Priority Sequence', default=10)
    category_name = fields.Char(string='Domain', default='Spending')
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)

    insight_type = fields.Selection([
        ('budget', 'Budget Alert'),
        ('savings', 'Savings Rate Trend'),
        ('cashflow', 'Cash Flow & Liquidity'),
        ('spending', 'Spending Anomaly'),
        ('goal', 'Goal Milestone'),
    ], string='Insight Type', default='spending', required=True)

    level = fields.Selection([
        ('danger', 'Critical Attention'),
        ('warning', 'Notice / Warning'),
        ('info', 'Observation'),
        ('success', 'Positive Milestone'),
    ], string='Severity Level', default='info', required=True)

    badge_text = fields.Char(string='Metric Highlight', placeholder='e.g. +45% or -$2,100')
    badge_subtext = fields.Char(string='Metric Context', placeholder='e.g. vs 3-month avg or of budget')
    description = fields.Text(string='Actionable Recommendation', required=True)

    action_type = fields.Char(string='Action Key')
    action_res_id = fields.Integer(string='Target Record ID')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        return res

    @api.model
    def get_user_insights(self):
        """Generate and return real-time smart financial insights."""
        today = fields.Date.context_today(self)
        user = self.env.user
        insights = []

        # -------------------------------------------------------------
        # 1. Budget Overspend & Warning Analyzer
        # -------------------------------------------------------------
        open_periods = self.env['moneta.budget.period'].search([
            ('budget_id.user_id', '=', user.id),
            ('status', '=', 'open'),
        ])
        for period in open_periods:
            for pc in period.period_category_ids:
                if pc.is_income or pc.budgeted_amount <= 0:
                    continue
                spent = abs(float(pc.actual_amount or 0.0))
                budgeted = float(pc.effective_budget or pc.budgeted_amount or 0.0)
                pct = (spent / budgeted) * 100.0 if budgeted > 0 else 0.0

                if pct >= 100.0:
                    insights.append({
                        'name': f"{pc.category_id.name} budget exceeded",
                        'category_name': f"Budget · {today.strftime('%B')}",
                        'insight_type': 'budget',
                        'level': 'danger',
                        'badge_text': f"{int(pct)}%",
                        'badge_subtext': "of budget",
                        'description': f"You have spent {int(pct)}% of your planned budget for {pc.category_id.name} ({spent:.2f} spent of {budgeted:.2f} limit).",
                        'action_type': 'open_budget',
                        'action_res_id': period.budget_id.id,
                        'sequence': 1,
                    })
                elif pct >= 80.0:
                    insights.append({
                        'name': f"{pc.category_id.name} is approaching budget limit",
                        'category_name': f"Budget · {today.strftime('%B')}",
                        'insight_type': 'budget',
                        'level': 'warning',
                        'badge_text': f"{int(pct)}%",
                        'badge_subtext': "of budget",
                        'description': f"You have reached {int(pct)}% of your {pc.category_id.name} budget with {calendar.monthrange(today.year, today.month)[1] - today.day} days left this month.",
                        'action_type': 'open_budget',
                        'action_res_id': period.budget_id.id,
                        'sequence': 5,
                    })

        # -------------------------------------------------------------
        # 2. 30-Day Cashflow Liquidity & Overdraft Warning
        # -------------------------------------------------------------
        checking_accs = self.env['moneta.account'].search([
            ('account_type', 'in', ('checking', 'chequing', 'cash')),
            ('user_id', '=', user.id),
            ('is_closed', '=', False),
        ])
        for acc in checking_accs:
            cur_bal = float(acc.current_balance or 0.0)
            proj_30 = float(acc.forecast_balance_30d or cur_bal)
            if proj_30 < 0:
                insights.append({
                    'name': f"Cash balance on {acc.name} may dip below $0",
                    'category_name': "Cash Flow · Next 30 Days",
                    'insight_type': 'cashflow',
                    'level': 'danger',
                    'badge_text': f"${proj_30:,.2f}",
                    'badge_subtext': "projected balance",
                    'description': f"Your current balance is ${cur_bal:,.2f}. Based on scheduled recurring bills, your balance is projected to reach ${proj_30:,.2f} in the next 30 days.",
                    'action_type': 'open_bills',
                    'sequence': 2,
                })

        # -------------------------------------------------------------
        # 3. Savings Rate Velocity (This Month vs Prior Month)
        # -------------------------------------------------------------
        m_start = today.replace(day=1)
        prev_m_start = (m_start - relativedelta(months=1))
        prev_m_end = m_start - timedelta(days=1)

        # Current Month
        txs_cur = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', m_start),
            ('transaction_date', '<=', today),
            ('state', '!=', 'void'),
            ('is_transfer', '=', False),
        ])
        inc_cur = sum(float(t.amount) for t in txs_cur if t.amount > 0)
        exp_cur = abs(sum(float(t.amount) for t in txs_cur if t.amount < 0))
        rate_cur = ((inc_cur - exp_cur) / inc_cur * 100.0) if inc_cur > 0 else 0.0

        # Prior Month
        txs_prev = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', prev_m_start),
            ('transaction_date', '<=', prev_m_end),
            ('state', '!=', 'void'),
            ('is_transfer', '=', False),
        ])
        inc_prev = sum(float(t.amount) for t in txs_prev if t.amount > 0)
        exp_prev = abs(sum(float(t.amount) for t in txs_prev if t.amount < 0))
        rate_prev = ((inc_prev - exp_prev) / inc_prev * 100.0) if inc_prev > 0 else 0.0

        if inc_cur > 0 and inc_prev > 0:
            diff_pp = rate_cur - rate_prev
            if diff_pp >= 5.0:
                insights.append({
                    'name': f"Your savings rate increased in {today.strftime('%B')}",
                    'category_name': f"Savings Rate · {today.strftime('%B')}",
                    'insight_type': 'savings',
                    'level': 'success',
                    'badge_text': f"+{diff_pp:.1f} pp",
                    'badge_subtext': "vs prior month",
                    'description': f"Your savings rate this month is {rate_cur:.1f}% compared to {rate_prev:.1f}% last month. Great job expanding your wealth buffer!",
                    'action_type': 'open_net_worth',
                    'sequence': 4,
                })
            elif diff_pp <= -5.0:
                insights.append({
                    'name': f"Your savings rate dropped in {today.strftime('%B')}",
                    'category_name': f"Savings Rate · {today.strftime('%B')}",
                    'insight_type': 'savings',
                    'level': 'warning',
                    'badge_text': f"{diff_pp:.1f} pp",
                    'badge_subtext': "vs prior month",
                    'description': f"Your savings rate is currently {rate_cur:.1f}% compared to {rate_prev:.1f}% last month. Consider reviewing recent discretionary outflows.",
                    'action_type': 'open_register',
                    'sequence': 3,
                })

        # -------------------------------------------------------------
        # 4. Spending Category Spike / Velocity Anomalies
        # -------------------------------------------------------------
        three_months_ago = today - timedelta(days=90)
        txs_90d = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', three_months_ago),
            ('transaction_date', '<', m_start),
            ('amount', '<', 0),
            ('state', '!=', 'void'),
            ('is_transfer', '=', False),
        ])
        cat_90d = {}
        for t in txs_90d:
            if t.category_id:
                cat_90d.setdefault(t.category_id, []).append(abs(float(t.amount)))

        # Current month category pacing
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        pacing_factor = days_in_month / max(today.day, 1)

        cat_cur = {}
        for t in txs_cur:
            if t.category_id and t.amount < 0:
                cat_cur.setdefault(t.category_id, 0.0)
                cat_cur[t.category_id] += abs(float(t.amount))

        for cat, spent_now in cat_cur.items():
            if cat in cat_90d and len(cat_90d[cat]) >= 2:
                avg_monthly_baseline = sum(cat_90d[cat]) / 3.0
                projected_month_spend = spent_now * pacing_factor

                if avg_monthly_baseline > 50.0:
                    pct_deviation = ((projected_month_spend - avg_monthly_baseline) / avg_monthly_baseline) * 100.0
                    if pct_deviation >= 40.0:
                        insights.append({
                            'name': f"{cat.name} spending is trending up",
                            'category_name': f"Spending Velocity · Day {today.day}",
                            'insight_type': 'spending',
                            'level': 'warning',
                            'badge_text': f"+{int(pct_deviation)}%",
                            'badge_subtext': "on pace vs baseline",
                            'description': f"Your projected {cat.name} spending is ${projected_month_spend:,.2f}, which is {int(pct_deviation)}% above your 3-month baseline of ${avg_monthly_baseline:,.2f}.",
                            'action_type': 'open_register',
                            'sequence': 6,
                        })
                    elif pct_deviation <= -40.0:
                        insights.append({
                            'name': f"{cat.name} spending is trending down",
                            'category_name': f"Spending Velocity · Day {today.day}",
                            'insight_type': 'spending',
                            'level': 'success',
                            'badge_text': f"{int(pct_deviation)}%",
                            'badge_subtext': "below baseline",
                            'description': f"Your projected {cat.name} spending is ${projected_month_spend:,.2f}, which is {abs(int(pct_deviation))}% below your historical baseline of ${avg_monthly_baseline:,.2f}.",
                            'action_type': 'open_register',
                            'sequence': 7,
                        })

        # -------------------------------------------------------------
        # 5. Financial Goal Milestones
        # -------------------------------------------------------------
        goals = self.env['moneta.goal'].search([
            ('user_id', '=', user.id),
            ('status', 'in', ('in_progress', 'achieved')),
        ])
        for g in goals:
            if g.status == 'achieved':
                insights.append({
                    'name': f"🎉 Milestone Achieved: {g.name}",
                    'category_name': "Goal Milestone",
                    'insight_type': 'goal',
                    'level': 'success',
                    'badge_text': "100%",
                    'badge_subtext': "Goal Reached",
                    'description': f"Congratulations! You reached your savings target of ${g.target_amount:,.2f} for '{g.name}'.",
                    'action_type': 'open_goals',
                    'sequence': 8,
                })
            elif g.progress_percent >= 85.0:
                insights.append({
                    'name': f"{g.name} is almost funded ({int(g.progress_percent)}%)",
                    'category_name': "Goal Milestone",
                    'insight_type': 'goal',
                    'level': 'info',
                    'badge_text': f"{int(g.progress_percent)}%",
                    'badge_subtext': "Completed",
                    'description': f"Only ${g.remaining_amount:,.2f} remaining to reach your full ${g.target_amount:,.2f} goal target.",
                    'action_type': 'open_goals',
                    'sequence': 9,
                })

        return sorted(insights, key=lambda x: x['sequence'])

    def action_execute_insight(self):
        """1-Click navigation based on the insight recommendation."""
        self.ensure_one()
        if self.action_type == 'open_budget':
            action = self.env.ref('moneta_finance.action_moneta_budget').read()[0]
            if self.action_res_id:
                action['views'] = [(self.env.ref('moneta_finance.view_moneta_budget_form').id, 'form')]
                action['res_id'] = self.action_res_id
            return action
        elif self.action_type == 'open_bills':
            return self.env.ref('moneta_finance.action_moneta_recurring').read()[0]
        elif self.action_type == 'open_goals':
            return self.env.ref('moneta_finance.action_moneta_goal').read()[0]
        elif self.action_type == 'open_net_worth':
            return self.env.ref('moneta_finance.action_moneta_net_worth').read()[0]
        else:
            return self.env.ref('moneta_finance.action_moneta_transaction').read()[0]
