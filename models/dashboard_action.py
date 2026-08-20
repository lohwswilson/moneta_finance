# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MonetaDashboardAction(models.Model):
    _name = 'moneta.dashboard.action'
    _description = 'Moneta Dynamic Dashboard Quick Action'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Button Label', required=True)
    sequence = fields.Integer(string='Order Sequence', default=10)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, index=True)
    active = fields.Boolean(string='Show on Dashboard', default=True)

    action_type = fields.Selection([
        ('accounts', 'Bank & Brokerage Accounts'),
        ('register', 'Transaction Register'),
        ('ai_chat', 'Ask Moneta AI Advisor'),
        ('ai_receipt', 'Scan Receipt / Invoice (AI OCR)'),
        ('rebalance', '1-Click Portfolio Rebalancer'),
        ('stock_split', 'Stock Split Corporate Action'),
        ('goals', 'Financial Goals & Sinking Funds'),
        ('properties', 'Real Estate, Vehicles & Valuables'),
        ('portfolio', 'Investment Portfolio Holdings'),
        ('target_alloc', 'Target Asset Allocation Matrix'),
        ('benchmark', 'Benchmark Analytics (vs S&P 500)'),
        ('bills', 'Bills & Scheduled Reminders'),
        ('budgets', 'Category Budgets'),
        ('rules', 'Transaction Automation Rules'),
        ('reconciliation', 'Bank Statement Reconciliation Wizard'),
        ('import', 'Import Financial Data (QIF/CSV)'),
        ('export', 'Export Register (QIF/CSV)'),
        ('loan', 'Loan & Mortgage Amortization'),
        ('monte_carlo', 'Monte Carlo Retirement Simulator'),
        ('emergency', 'Emergency Digital Estate Access'),
        ('insights', 'Smart Financial Insights'),
        ('net_worth', 'Net Worth Trend & Analytics'),
        ('custom', 'Custom Window Action (Advanced)'),
    ], string='Target Action', default='register', required=True)

    custom_action_id = fields.Many2one('ir.actions.act_window', string='Custom Window Action')

    icon = fields.Char(string='Icon Class (FontAwesome)', default='fa-bolt', required=True)
    color_class = fields.Selection([
        ('primary', 'Solid Primary (Blue)'),
        ('outline_primary', 'Outline Primary (Blue)'),
        ('outline_success', 'Outline Success (Green)'),
        ('outline_danger', 'Outline Alert (Red)'),
        ('outline_warning', 'Outline Warning (Amber)'),
        ('outline_info', 'Outline Info (Cyan)'),
        ('outline_dark', 'Outline Dark (Black/Navy)'),
        ('outline_secondary', 'Outline Muted (Gray)'),
    ], string='Button Style', default='outline_primary', required=True)

    @api.onchange('action_type')
    def _onchange_action_type(self):
        defaults = {
            'accounts': ('Bank & Brokerage Accounts', 'fa-university', 'outline_primary'),
            'register': ('Transaction Register', 'fa-book', 'primary'),
            'ai_chat': ('Ask Moneta AI', 'fa-comments', 'outline_primary'),
            'ai_receipt': ('Scan Receipt OCR', 'fa-camera', 'outline_info'),
            'rebalance': ('1-Click Rebalancer', 'fa-balance-scale', 'outline_success'),
            'stock_split': ('Stock Split Action', 'fa-scissors', 'outline_warning'),
            'goals': ('Financial Goals', 'fa-bullseye', 'outline_success'),
            'properties': ('Real Estate & Valuables', 'fa-home', 'outline_info'),
            'portfolio': ('Investment Portfolio', 'fa-pie-chart', 'outline_dark'),
            'target_alloc': ('Target Asset Allocation', 'fa-sliders', 'outline_primary'),
            'benchmark': ('Benchmark vs S&P 500', 'fa-line-chart', 'outline_dark'),
            'bills': ('Bills & Reminders', 'fa-calendar', 'outline_danger'),
            'budgets': ('Category Budgets', 'fa-th-list', 'outline_warning'),
            'rules': ('Transaction Rules', 'fa-magic', 'outline_secondary'),
            'reconciliation': ('Reconcile Statement', 'fa-check-square-o', 'outline_dark'),
            'import': ('Import QIF / CSV', 'fa-upload', 'outline_secondary'),
            'export': ('Export Register', 'fa-download', 'outline_secondary'),
            'loan': ('Loan Amortization', 'fa-calculator', 'outline_info'),
            'monte_carlo': ('Monte Carlo Simulator', 'fa-random', 'outline_success'),
            'emergency': ('Emergency Estate', 'fa-shield', 'outline_danger'),
            'insights': ('Smart Insights', 'fa-lightbulb-o', 'outline_warning'),
            'net_worth': ('Net Worth Trend', 'fa-area-chart', 'outline_primary'),
        }
        if self.action_type in defaults:
            lbl, ico, col = defaults[self.action_type]
            self.name = lbl
            self.icon = ico
            self.color_class = col

    def action_execute(self):
        """Dispatch the configured action dynamically."""
        self.ensure_one()
        mapping = {
            'accounts': 'moneta_finance.action_moneta_account',
            'register': 'moneta_finance.action_moneta_transaction',
            'ai_chat': 'moneta_finance.action_moneta_ai_chat',
            'ai_receipt': 'moneta_finance.action_moneta_ai_receipt_wizard',
            'rebalance': 'moneta_finance.action_moneta_rebalance_wizard',
            'stock_split': 'moneta_finance.action_moneta_stock_split_wizard',
            'goals': 'moneta_finance.action_moneta_goal',
            'properties': 'moneta_finance_property.action_moneta_property',
            'portfolio': 'moneta_finance.action_moneta_holding',
            'target_alloc': 'moneta_finance.action_moneta_target_allocation',
            'benchmark': 'moneta_finance.action_moneta_benchmark',
            'bills': 'moneta_finance.action_moneta_recurring',
            'budgets': 'moneta_finance.action_moneta_budget',
            'rules': 'moneta_finance.action_moneta_transaction_rule',
            'reconciliation': 'moneta_finance.action_moneta_reconciliation_wizard',
            'import': 'moneta_finance.action_moneta_import_wizard',
            'export': 'moneta_finance.action_moneta_export_wizard',
            'loan': 'moneta_finance.action_moneta_loan',
            'monte_carlo': 'moneta_finance.action_moneta_monte_carlo',
            'emergency': 'moneta_finance.action_moneta_emergency_contact',
            'insights': 'moneta_finance.action_moneta_insight',
            'net_worth': 'moneta_finance.action_moneta_net_worth',
        }

        if self.action_type == 'custom' and self.custom_action_id:
            return self.custom_action_id.read()[0]

        xml_id = mapping.get(self.action_type)
        action_ref = self.env.ref(xml_id, raise_if_not_found=False) if xml_id else None
        if not action_ref and self.action_type == 'properties':
            action_ref = self.env.ref('moneta_finance.action_moneta_property', raise_if_not_found=False)
        if not action_ref:
            action_ref = self.env.ref('moneta_finance.action_moneta_transaction', raise_if_not_found=False)

        if not action_ref:
            return {'type': 'ir.actions.act_window_close'}
        action = action_ref.read()[0]
        return action

    @api.model
    def seed_user_default_actions(self, user=None):
        """Seed default 10 launcher buttons for a user if empty."""
        user = user or self.env.user
        existing = self.search_count([('user_id', '=', user.id)])
        if existing > 0:
            return

        defaults = [
            ('Accounts & Banks', 5, 'accounts', 'fa-university', 'outline_primary'),
            ('Transaction Register', 10, 'register', 'fa-book', 'primary'),
            ('Ask Moneta AI', 20, 'ai_chat', 'fa-comments', 'outline_primary'),
            ('Scan Receipt OCR', 30, 'ai_receipt', 'fa-camera', 'outline_info'),
            ('Financial Goals', 40, 'goals', 'fa-bullseye', 'outline_success'),
            ('1-Click Rebalancer', 50, 'rebalance', 'fa-balance-scale', 'outline_success'),
            ('Investment Portfolio', 60, 'portfolio', 'fa-pie-chart', 'outline_dark'),
            ('Bills & Reminders', 70, 'bills', 'fa-calendar', 'outline_danger'),
            ('Category Budgets', 80, 'budgets', 'fa-th-list', 'outline_warning'),
            ('Real Estate & Valuables', 90, 'properties', 'fa-home', 'outline_info'),
            ('Reconcile Statement', 100, 'reconciliation', 'fa-check-square-o', 'outline_dark'),
            ('Smart Insights', 110, 'insights', 'fa-lightbulb-o', 'outline_warning'),
            ('Net Worth Trend', 120, 'net_worth', 'fa-area-chart', 'outline_primary'),
        ]

        vals = []
        for name, seq, act_type, icon, color in defaults:
            vals.append({
                'name': name,
                'sequence': seq,
                'action_type': act_type,
                'icon': icon,
                'color_class': color,
                'user_id': user.id,
                'active': True,
            })
        self.create(vals)
