# -*- coding: utf-8 -*-
{
    'name': 'Moneta Personal Finance',
    'version': '18.0.3.1.0',
    'category': 'Accounting/Finance',
    'summary': 'Personal finance manager: bank accounts, credit cards, investments, budgets & QIF/OFX imports.',
    'description': """
Moneta Personal Finance for Odoo
================================
A comprehensive personal finance management module built for Odoo.

Features:
---------
* Multi-account management: Chequing, Savings, Credit Cards, Mortgages, Loans, Line of Credit, Brokerages.
* Joint Accounts & Multi-user Sharing: Shared registers and cross-owner visibility with granular permissions.
* Transactions, split transactions, auto-categorization & payee analytics (YoY spending & recurring cadence).
* Multi-currency support for accounts, transactions, and scheduled recurring bills.
* Investments: Ticker master, daily stock prices, portfolio holdings, multi-asset class weighting & fact sheets.
* GEM Strategy: Global Equities Momentum dual-momentum allocation rule and signal generator.
* Category budgets with planned vs. actual spent tracking.
* Scheduled & recurring transaction automation with extended frequencies.
* Import wizard: QIF, OFX/QFX, and CSV files.
* Financial reports: Monthly spending, net worth history, pivot & graph analytics.
    """,
    'author': 'Moneta Community',
    'website': 'https://github.com/lohwswilson/moneta_finance',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'pre_init_hook': '_pre_init_migrate_category_type',
    'post_init_hook': '_post_init_seed_defaults',
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/moneta_record_rules.xml',
        'data/default_categories.xml',
        'data/moneta_cron.xml',
        'views/category_views.xml',
        'views/payee_views.xml',
        'views/account_views.xml',
        'views/institution_views.xml',
        'views/transaction_views.xml',
        'views/investment_views.xml',
        'views/gem_strategy_views.xml',
        'views/budget_views.xml',
        'views/recurring_views.xml',
        'views/tag_views.xml',
        'views/dashboard_views.xml',
        'views/loan_views.xml',
        'views/monte_carlo_views.xml',
        'views/emergency_views.xml',
        'views/rule_views.xml',
        'views/goal_views.xml',
        'views/property_views.xml',
        'views/subscription_detector_views.xml',
        'views/net_worth_views.xml',
        'views/wizard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'moneta_finance/static/src/css/moneta_style.css',
        ],
    },
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
