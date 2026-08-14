# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta
from odoo import models, fields, api


class MonetaDashboard(models.TransientModel):
    _name = 'moneta.dashboard'
    _description = 'Moneta Quicken Premier Dashboard'

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
            for acc in accounts:
                bal = float(acc.current_balance or 0.0)
                if acc.account_type in ('credit_card', 'loan', 'mortgage', 'loc'):
                    if bal < 0:
                        liabilities += abs(bal)
                    else:
                        liabilities += bal
                else:
                    if bal > 0:
                        assets += bal
                    else:
                        assets += bal
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
            dash.month_net_savings = round(income + expenses, 4)  # expenses are negative in amount
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

    def action_recompute(self):
        self.invalidate_recordset()
        return True

    def action_open_accounts(self):
        return {
            'name': 'Financial Accounts',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.account',
            'view_mode': 'kanban,list,form',
        }

    def action_open_register(self):
        return {
            'name': 'Checkbook Register',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.transaction',
            'view_mode': 'list,form,pivot,graph',
        }

    def action_open_portfolio(self):
        return {
            'name': 'Portfolio Holdings',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.holding',
            'view_mode': 'list,form,graph',
        }

    def action_open_bills(self):
        return {
            'name': 'Bills & Scheduled Transactions',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.recurring.transaction',
            'view_mode': 'list,form',
        }

    def action_open_budgets(self):
        return {
            'name': 'Category Budgets',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.budget',
            'view_mode': 'list,form',
        }

    def action_open_net_worth(self):
        return {
            'name': 'Net Worth Trend',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.net.worth',
            'view_mode': 'list,graph',
        }

    def action_open_reconciliation(self):
        return {
            'name': 'Reconcile Account Statement',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.reconciliation.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_import(self):
        return {
            'name': 'Import Financial Data',
            'type': 'ir.actions.act_window',
            'res_model': 'moneta.import.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
