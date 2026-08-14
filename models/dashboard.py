# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta
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

    @api.depends('name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Dashboard'

    @api.depends()
    def _compute_totals(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        for dash in self:
            # Net worth and monthly balances
            dash.net_worth = self.env['moneta.account.balance.monthly']._net_worth_for_month(month_start)
            
            # Active accounts breakdown
            accounts = self.env['moneta.account'].search([('is_closed', '=', False), ('exclude_from_net_worth', '=', False)])
            dash.account_count = len(accounts)
            assets = 0.0
            liabilities = 0.0
            cash_tot = 0.0
            inv_tot = 0.0
            cc_tot = 0.0
            loan_tot = 0.0

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

            dash.cash_assets = round(cash_tot, 4)
            dash.investment_assets = round(inv_tot, 4)
            dash.credit_card_debt = round(cc_tot, 4)
            dash.loans_mortgages_debt = round(loan_tot, 4)
            dash.total_assets = round(max(assets, 0.0), 4)
            dash.total_liabilities = round(max(liabilities, 0.0), 4)

            # Month income/expense from non-void transactions
            txs = self.env['moneta.transaction'].search([
                ('transaction_date', '>=', month_start),
                ('transaction_date', '<=', month_end),
                ('state', '!=', 'void'),
            ])
            income = 0.0
            expenses = 0.0
            for tx in txs:
                if tx.amount > 0:
                    income += float(tx.amount or 0.0)
                else:
                    expenses += float(tx.amount or 0.0)
            dash.month_income = round(income, 4)
            dash.month_expenses = round(-expenses, 4)
            dash.month_net_savings = round(income + expenses, 4)
            dash.savings_rate = round((dash.month_net_savings / income * 100.0), 2) if income > 0 else 0.0

    @api.depends()
    def _compute_upcoming_bills(self):
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=14)
        for dash in self:
            scheds = self.env['moneta.recurring.transaction'].search([
                ('active', '=', True),
                ('next_date', '>=', today),
                ('next_date', '<=', horizon),
                ('amount', '<', 0),
            ])
            dash.upcoming_bill_count = len(scheds)
            dash.upcoming_bills_total = round(-sum(float(s.amount or 0.0) for s in scheds), 4)

    @api.depends()
    def _compute_investment_totals(self):
        for dash in self:
            holdings = self.env['moneta.holding'].search([])
            dash.holding_count = len(holdings)
            mkt_val = sum(float(h.market_value or 0.0) for h in holdings)
            basis = sum(float(h.cost_basis or 0.0) for h in holdings)
            dash.portfolio_market_value = round(mkt_val, 4)
            dash.portfolio_cost_basis = round(basis, 4)
            dash.portfolio_unrealized_gain = round(mkt_val - basis, 4)
            dash.portfolio_gain_percent = round(((dash.portfolio_unrealized_gain / basis) * 100.0), 2) if basis > 0 else 0.0

    @api.depends()
    def _compute_fire_and_real_estate(self):
        today = fields.Date.context_today(self)
        three_months_ago = today - timedelta(days=90)
        for dash in self:
            # 1. Real Estate Equity & Valuation
            props = self.env['moneta.property'].search([])
            dash.real_estate_assets = round(sum(float(p.current_market_value or 0.0) for p in props), 4)
            dash.total_real_estate_equity = round(sum(float(p.equity_value or 0.0) for p in props), 4)

            # 2. Monthly Burn Rate (last 90 days average expenses)
            txs = self.env['moneta.transaction'].search([
                ('transaction_date', '>=', three_months_ago),
                ('transaction_date', '<=', today),
                ('amount', '<', 0),
                ('state', '!=', 'void'),
            ])
            total_90d_exp = abs(sum(float(t.amount or 0.0) for t in txs))
            monthly_burn = (total_90d_exp / 3.0) if total_90d_exp > 0 else float(dash.month_expenses or 3000.0)
            if monthly_burn <= 0:
                monthly_burn = 3000.0

            # 3. Liquid Assets (Chequing, Savings, Cash, Brokerages)
            liquid_accs = self.env['moneta.account'].search([
                ('account_type', 'in', ('chequing', 'savings', 'cash', 'brokerage')),
                ('is_closed', '=', False),
            ])
            liquid_total = sum(max(float(a.current_balance or 0.0), 0.0) for a in liquid_accs)
            dash.emergency_runway_months = round(liquid_total / monthly_burn, 1)

            # 4. FIRE Target = 25x Annual Expenses (or 300x Monthly Burn)
            annual_exp = monthly_burn * 12.0
            dash.fire_target_amount = round(annual_exp * 25.0, 4)
            nw = float(dash.net_worth or 0.0) + float(dash.total_real_estate_equity or 0.0)
            if dash.fire_target_amount > 0:
                dash.fire_progress_pct = round(min(max((nw / dash.fire_target_amount) * 100.0, 0.0), 100.0), 1)
            else:
                dash.fire_progress_pct = 0.0

    def action_recompute(self):
        self.invalidate_recordset()
        return True

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
