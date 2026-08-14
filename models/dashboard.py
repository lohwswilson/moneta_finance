# -*- coding: utf-8 -*-
import calendar
from datetime import date, timedelta
from odoo import models, fields, api


class MonetaDashboard(models.TransientModel):
    _name = 'moneta.dashboard'
    _description = 'Moneta Quicken Premier & Wealth Dashboard'
    _rec_name = 'name'

    name = fields.Char(string='Name', default='Dashboard')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, required=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user, required=True, index=True,
    )

    # Net Worth & Wealth
    net_worth = fields.Monetary(string='Net Worth', compute='_compute_totals')
    total_assets = fields.Monetary(string='Total Assets', compute='_compute_totals')
    total_liabilities = fields.Monetary(string='Total Liabilities', compute='_compute_totals')
    account_count = fields.Integer(string='Active Accounts', compute='_compute_totals')

    # Asset Breakdown (Sure Style)
    cash_assets = fields.Monetary(string='Cash & Banks', compute='_compute_totals')
    investment_assets = fields.Monetary(string='Investments & Stocks', compute='_compute_totals')
    real_estate_assets = fields.Monetary(string='Real Estate & Property', compute='_compute_fire_and_real_estate')
    credit_card_debt = fields.Monetary(string='Credit Cards', compute='_compute_totals')
    loans_mortgages_debt = fields.Monetary(string='Loans & Mortgages', compute='_compute_totals')

    # Cash Flow & Savings
    month_income = fields.Monetary(string='This Month Income', compute='_compute_totals')
    month_expenses = fields.Monetary(string='This Month Expenses', compute='_compute_totals')
    month_net_savings = fields.Monetary(string='Net Savings', compute='_compute_totals')
    savings_rate = fields.Float(string='Savings Rate (%)', compute='_compute_totals', digits=(5, 2))

    # Bills & Reminders
    upcoming_bill_count = fields.Integer(string='Upcoming Bills (14 days)', compute='_compute_upcoming_bills')
    upcoming_bills_total = fields.Monetary(string='Upcoming Bills Total', compute='_compute_upcoming_bills')

    # Investment Portfolio
    portfolio_market_value = fields.Monetary(string='Portfolio Market Value', compute='_compute_investment_totals')
    portfolio_cost_basis = fields.Monetary(string='Total Cost Basis', compute='_compute_investment_totals')
    portfolio_unrealized_gain = fields.Monetary(string='Unrealized Gain / Loss', compute='_compute_investment_totals')
    portfolio_gain_percent = fields.Float(string='Portfolio Gain (%)', compute='_compute_investment_totals', digits=(5, 2))
    holding_count = fields.Integer(string='Holdings Count', compute='_compute_investment_totals')

    # FIRE & Financial Freedom Metrics (Sure Inspired)
    emergency_runway_months = fields.Float(string='Runway (Months)', compute='_compute_fire_and_real_estate', digits=(5, 1))
    fire_target_amount = fields.Monetary(string='FIRE Target ($)', compute='_compute_fire_and_real_estate')
    fire_progress_pct = fields.Float(string='FIRE Progress (%)', compute='_compute_fire_and_real_estate', digits=(5, 1))
    total_real_estate_equity = fields.Monetary(string='Real Estate Equity', compute='_compute_fire_and_real_estate')

    # Smart Financial Insights (Sure-Style)
    insight_count = fields.Integer(string='Insights Count', compute='_compute_insights')
    top_insight_title = fields.Char(string='Top Insight', compute='_compute_insights')
    top_insight_badge = fields.Char(string='Top Insight Badge', compute='_compute_insights')
    top_insight_desc = fields.Text(string='Top Insight Recommendation', compute='_compute_insights')
    top_insight_level = fields.Selection([
        ('danger', 'Critical Attention'),
        ('warning', 'Notice / Warning'),
        ('info', 'Observation'),
        ('success', 'Positive Milestone'),
    ], string='Top Insight Severity', compute='_compute_insights')

    # Dynamic Quick Action Launchpad (Customizable)
    action_launchpad_ids = fields.Many2many('moneta.dashboard.action', string='Dynamic Quick Actions', compute='_compute_launchpad_actions')

    @api.model
    def default_get(self, fields_list):
        """Pre-populate all dashboard KPIs on initial form load so values are never 0.00."""
        res = super().default_get(fields_list)
        user = self.env.user
        today = date.today()
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        three_months_ago = today - timedelta(days=90)
        horizon = today + timedelta(days=14)

        # 1. Accounts & Balances
        accounts = self.env['moneta.account'].search([
            ('user_id', '=', user.id),
            ('is_closed', '=', False),
            ('exclude_from_net_worth', '=', False),
        ])
        res['account_count'] = len(accounts)
        cash_tot, inv_tot, cc_tot, loan_tot = 0.0, 0.0, 0.0, 0.0

        for acc in accounts:
            bal = float(acc.current_balance or 0.0)
            if acc.account_type in ('credit_card',):
                cc_tot += abs(bal) if bal < 0 else bal
            elif acc.account_type in ('loan', 'mortgage', 'loc'):
                loan_tot += abs(bal) if bal < 0 else bal
            elif acc.account_type in ('brokerage', 'retirement', 'crypto'):
                inv_tot += bal if bal > 0 else bal
            else:
                cash_tot += bal if bal > 0 else bal

        res['cash_assets'] = round(cash_tot, 4)
        res['investment_assets'] = round(inv_tot, 4)
        res['credit_card_debt'] = round(cc_tot, 4)
        res['loans_mortgages_debt'] = round(loan_tot, 4)
        total_liab = cc_tot + loan_tot
        res['total_liabilities'] = round(total_liab, 4)

        # 2. Real Estate & Tangible Assets
        props = self.env['moneta.property'].search([('user_id', '=', user.id)])
        re_mkt, re_eq = 0.0, 0.0
        for p in props:
            val = float(p.current_market_value or 0.0)
            debt = abs(float(p.mortgage_account_id.current_balance or 0.0)) if p.mortgage_account_id else float(p.mortgage_balance or 0.0)
            re_mkt += val
            re_eq += max(val - debt, 0.0)

        res['real_estate_assets'] = round(re_mkt, 4)
        res['total_real_estate_equity'] = round(re_eq, 4)
        total_ass = cash_tot + inv_tot + re_mkt
        res['total_assets'] = round(total_ass, 4)
        res['net_worth'] = round(total_ass - total_liab, 4)

        # 3. Monthly Income & Expenses
        txs = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', month_start),
            ('transaction_date', '<=', month_end),
            ('state', '!=', 'void'),
        ])
        inc, exp = 0.0, 0.0
        for tx in txs:
            if tx.amount > 0:
                inc += float(tx.amount or 0.0)
            else:
                exp += float(tx.amount or 0.0)
        res['month_income'] = round(inc, 4)
        res['month_expenses'] = round(-exp, 4)
        res['month_net_savings'] = round(inc + exp, 4)
        res['savings_rate'] = round(((inc + exp) / inc * 100.0), 2) if inc > 0 else 0.0

        # 4. Investment Holdings
        holdings = self.env['moneta.holding'].search([('user_id', '=', user.id)])
        res['holding_count'] = len(holdings)
        mkt_v = sum(float(h.market_value or 0.0) for h in holdings)
        c_bas = sum(float(h.cost_basis or 0.0) for h in holdings)
        res['portfolio_market_value'] = round(mkt_v, 4)
        res['portfolio_cost_basis'] = round(c_bas, 4)
        res['portfolio_unrealized_gain'] = round(mkt_v - c_bas, 4)
        res['portfolio_gain_percent'] = round(((mkt_v - c_bas) / c_bas * 100.0), 2) if c_bas > 0 else 0.0

        # 5. Upcoming Bills
        scheds = self.env['moneta.recurring.transaction'].search([
            ('user_id', '=', user.id),
            ('active', '=', True),
            ('next_date', '>=', today),
            ('next_date', '<=', horizon),
            ('amount', '<', 0),
        ])
        res['upcoming_bill_count'] = len(scheds)
        res['upcoming_bills_total'] = round(-sum(float(s.amount or 0.0) for s in scheds), 4)

        # 6. Runway & FIRE
        txs_90 = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', three_months_ago),
            ('transaction_date', '<=', today),
            ('amount', '<', 0),
            ('state', '!=', 'void'),
        ])
        tot_90_exp = abs(sum(float(t.amount or 0.0) for t in txs_90))
        m_burn = (tot_90_exp / 3.0) if tot_90_exp > 0 else float(-exp or 3000.0)
        if m_burn <= 0:
            m_burn = 3000.0
        liquid_tot = cash_tot + inv_tot
        res['emergency_runway_months'] = round(liquid_tot / m_burn, 1)
        res['fire_target_amount'] = round(m_burn * 12.0 * 25.0, 4)
        if res['fire_target_amount'] > 0:
            res['fire_progress_pct'] = round(min(max((res['net_worth'] / res['fire_target_amount']) * 100.0, 0.0), 100.0), 1)
        else:
            res['fire_progress_pct'] = 0.0

        return res

    @api.depends('user_id', 'currency_id')
    def _compute_totals(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        for dash in self:
            user = dash.user_id or self.env.user
            accounts = self.env['moneta.account'].search([
                ('user_id', '=', user.id),
                ('is_closed', '=', False),
                ('exclude_from_net_worth', '=', False),
            ])
            dash.account_count = len(accounts)
            assets, liabilities = 0.0, 0.0
            cash_tot, inv_tot, cc_tot, loan_tot = 0.0, 0.0, 0.0, 0.0

            for acc in accounts:
                bal = float(acc.current_balance or 0.0)
                if acc.account_type in ('credit_card',):
                    cc_tot += abs(bal) if bal < 0 else bal
                    liabilities += abs(bal) if bal < 0 else bal
                elif acc.account_type in ('loan', 'mortgage', 'loc'):
                    loan_tot += abs(bal) if bal < 0 else bal
                    liabilities += abs(bal) if bal < 0 else bal
                elif acc.account_type in ('brokerage', 'retirement', 'crypto'):
                    inv_tot += bal if bal > 0 else bal
                    assets += bal if bal > 0 else bal
                else:
                    cash_tot += bal if bal > 0 else bal
                    assets += bal if bal > 0 else bal

            # Add Real Estate Assets into Total Assets & Net Worth
            props = self.env['moneta.property'].search([('user_id', '=', user.id)])
            re_mkt = sum(float(p.current_market_value or 0.0) for p in props)
            assets += re_mkt

            dash.cash_assets = round(cash_tot, 4)
            dash.investment_assets = round(inv_tot, 4)
            dash.credit_card_debt = round(cc_tot, 4)
            dash.loans_mortgages_debt = round(loan_tot, 4)
            dash.total_assets = round(max(assets, 0.0), 4)
            dash.total_liabilities = round(max(liabilities, 0.0), 4)
            dash.net_worth = round(assets - liabilities, 4)

            # Month income/expense from non-void transactions
            txs = self.env['moneta.transaction'].search([
                ('user_id', '=', user.id),
                ('transaction_date', '>=', month_start),
                ('transaction_date', '<=', month_end),
                ('state', '!=', 'void'),
            ])
            income, expenses = 0.0, 0.0
            for tx in txs:
                if tx.amount > 0:
                    income += float(tx.amount or 0.0)
                else:
                    expenses += float(tx.amount or 0.0)
            dash.month_income = round(income, 4)
            dash.month_expenses = round(-expenses, 4)
            dash.month_net_savings = round(income + expenses, 4)
            dash.savings_rate = round((dash.month_net_savings / income * 100.0), 2) if income > 0 else 0.0

    @api.depends('user_id', 'currency_id')
    def _compute_upcoming_bills(self):
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=14)
        for dash in self:
            user = dash.user_id or self.env.user
            scheds = self.env['moneta.recurring.transaction'].search([
                ('user_id', '=', user.id),
                ('active', '=', True),
                ('next_date', '>=', today),
                ('next_date', '<=', horizon),
                ('amount', '<', 0),
            ])
            dash.upcoming_bill_count = len(scheds)
            dash.upcoming_bills_total = round(-sum(float(s.amount or 0.0) for s in scheds), 4)

    @api.depends('user_id', 'currency_id')
    def _compute_investment_totals(self):
        for dash in self:
            user = dash.user_id or self.env.user
            holdings = self.env['moneta.holding'].search([('user_id', '=', user.id)])
            dash.holding_count = len(holdings)
            mkt_val = sum(float(h.market_value or 0.0) for h in holdings)
            basis = sum(float(h.cost_basis or 0.0) for h in holdings)
            dash.portfolio_market_value = round(mkt_val, 4)
            dash.portfolio_cost_basis = round(basis, 4)
            dash.portfolio_unrealized_gain = round(mkt_val - basis, 4)
            dash.portfolio_gain_percent = round(((dash.portfolio_unrealized_gain / basis) * 100.0), 2) if basis > 0 else 0.0

    @api.depends('user_id', 'currency_id')
    def _compute_fire_and_real_estate(self):
        today = fields.Date.context_today(self)
        three_months_ago = today - timedelta(days=90)
        for dash in self:
            user = dash.user_id or self.env.user
            # 1. Real Estate Equity & Valuation
            props = self.env['moneta.property'].search([('user_id', '=', user.id)])
            total_mkt = 0.0
            total_eq = 0.0
            for p in props:
                val = float(p.current_market_value or 0.0)
                debt = abs(float(p.mortgage_account_id.current_balance or 0.0)) if p.mortgage_account_id else float(p.mortgage_balance or 0.0)
                total_mkt += val
                total_eq += max(val - debt, 0.0)

            dash.real_estate_assets = round(total_mkt, 4)
            dash.total_real_estate_equity = round(total_eq, 4)

            # 2. Monthly Burn Rate (last 90 days average expenses)
            txs = self.env['moneta.transaction'].search([
                ('user_id', '=', user.id),
                ('transaction_date', '>=', three_months_ago),
                ('transaction_date', '<=', today),
                ('amount', '<', 0),
                ('state', '!=', 'void'),
            ])
            total_90d_exp = abs(sum(float(t.amount or 0.0) for t in txs))
            monthly_burn = (total_90d_exp / 3.0) if total_90d_exp > 0 else float(dash.month_expenses or 3000.0)
            if monthly_burn <= 0:
                monthly_burn = 3000.0

            # 3. Liquid Assets (Checking, Savings, Cash, Brokerages)
            liquid_accs = self.env['moneta.account'].search([
                ('user_id', '=', user.id),
                ('account_type', 'in', ('checking', 'chequing', 'savings', 'cash', 'brokerage')),
                ('is_closed', '=', False),
            ])
            liquid_total = sum(max(float(a.current_balance or 0.0), 0.0) for a in liquid_accs)
            dash.emergency_runway_months = round(liquid_total / monthly_burn, 1)

            # 4. FIRE Target = 25x Annual Expenses (or 300x Monthly Burn)
            annual_exp = monthly_burn * 12.0
            dash.fire_target_amount = round(annual_exp * 25.0, 4)
            nw = float(dash.net_worth or 0.0)
            if dash.fire_target_amount > 0:
                dash.fire_progress_pct = round(min(max((nw / dash.fire_target_amount) * 100.0, 0.0), 100.0), 1)
            else:
                dash.fire_progress_pct = 0.0

    def action_recompute(self):
        """Force re-compute all dashboard KPIs."""
        self.invalidate_recordset()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_accounts(self):
        action = self.env.ref('moneta_finance.action_moneta_account').read()[0]
        action['target'] = 'current'
        return action

    def action_open_register(self):
        action = self.env.ref('moneta_finance.action_moneta_transaction').read()[0]
        action['target'] = 'current'
        return action

    def action_open_portfolio(self):
        action = self.env.ref('moneta_finance.action_moneta_holding').read()[0]
        action['target'] = 'current'
        return action

    def action_open_bills(self):
        action = self.env.ref('moneta_finance.action_moneta_recurring').read()[0]
        action['target'] = 'current'
        return action

    def action_open_budgets(self):
        action = self.env.ref('moneta_finance.action_moneta_budget').read()[0]
        action['target'] = 'current'
        return action

    def action_open_net_worth(self):
        action = self.env.ref('moneta_finance.action_moneta_net_worth').read()[0]
        action['target'] = 'current'
        return action

    def action_open_goals(self):
        action = self.env.ref('moneta_finance.action_moneta_goal').read()[0]
        action['target'] = 'current'
        return action

    def action_open_properties(self):
        action = self.env.ref('moneta_finance.action_moneta_property').read()[0]
        action['target'] = 'current'
        return action

    def action_open_rules(self):
        action = self.env.ref('moneta_finance.action_moneta_transaction_rule').read()[0]
        action['target'] = 'current'
        return action

    def action_open_reconciliation(self):
        action = self.env.ref('moneta_finance.action_moneta_reconciliation_wizard').read()[0]
        action['target'] = 'new'
        return action

    def action_open_import(self):
        action = self.env.ref('moneta_finance.action_moneta_import_wizard').read()[0]
        action['target'] = 'new'
        return action

    @api.depends('user_id')
    def _compute_insights(self):
        for dash in self:
            insights = self.env['moneta.insight'].get_user_insights()
            dash.insight_count = len(insights)
            if insights:
                top = insights[0]
                dash.top_insight_title = top.get('name')
                badge_txt = top.get('badge_text', '')
                badge_sub = top.get('badge_subtext', '')
                dash.top_insight_badge = f"{badge_txt} {badge_sub}".strip()
                dash.top_insight_desc = top.get('description')
                dash.top_insight_level = top.get('level', 'info')
            else:
                dash.top_insight_title = 'All systems healthy'
                dash.top_insight_badge = 'On Track'
                dash.top_insight_desc = 'No budget overspends, cashflow dips, or anomalous spending spikes detected.'
                dash.top_insight_level = 'success'

    def action_open_insights(self):
        action = self.env.ref('moneta_finance.action_moneta_insight').read()[0]
        action['target'] = 'current'
        return action

    @api.depends('user_id')
    def _compute_launchpad_actions(self):
        ActionModel = self.env['moneta.dashboard.action']
        user = self.env.user
        ActionModel.seed_user_default_actions(user)
        actions = ActionModel.search([('user_id', '=', user.id), ('active', '=', True)], order='sequence asc, id asc')
        for dash in self:
            dash.action_launchpad_ids = actions

    def action_customize_launchpad(self):
        """Open the Launchpad Configuration Manager."""
        ActionModel = self.env['moneta.dashboard.action']
        ActionModel.seed_user_default_actions(self.env.user)
        action = self.env.ref('moneta_finance.action_moneta_dashboard_action').read()[0]
        action['target'] = 'current'
        return action
