# -*- coding: utf-8 -*-
{
    'name': 'Moneta Personal Finance',
    'version': '18.0.6.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Personal finance & wealth OS: Quicken-style registers, investments, budgets, loans, Monte Carlo, real estate, vehicles, antiques & FIRE analytics.',
    'description': """
Moneta Personal Finance for Odoo 18
===================================
A premier personal wealth management, budgeting, and investment operating system built for Odoo.

Key Features & Capabilities:
----------------------------
* **Banking & Checkbook Registers**:
  - Real-time cumulative running balances in register list views.
  - 1-Click `Clr` status toggle directly on rows (Unreconciled / Cleared / Reconciled).
  - Payee QuickFill (auto-fills category, amount, memo, and tags from history).
  - Multi-line split transactions with mathematical sum verification.
  - Interactive Bank Statement Reconciliation Wizard with live $0.00 difference target.
  - Transaction bulk server actions: Batch Cleared, Reconcile, and Batch Categorize wizard.
  - QIF / OFX / CSV file import and 1-click Checkbook Register QIF / CSV export wizard.

* **Investments & Wealthfolio Portfolio Analytics**:
  - Ticker master, daily stock quotes, and multi-lot portfolio holdings with average cost basis.
  - Time-Weighted Return (TWR %) and Money-Weighted Return (MWR / IRR %) performance metrics.
  - Dividend calendar & yield forecaster with annual estimated dividend income.
  - Target Asset Allocation matrix & 1-Click Portfolio Rebalancer wizard.
  - Benchmark index comparison against S&P 500 / VOO with Alpha ($\alpha$) excess returns.
  - Stock Split Corporate Action wizard (2:1, 3:1, 4:1, 10:1) with seamless basis preservation.
  - Global Equities Momentum (GEM) 12-month dual-momentum allocation engine.

* **Tangible Assets, Real Estate, Vehicles & Antiques**:
  - Real estate properties with mortgage debt linkage, net home equity ($), and LTV %.
  - Vehicle & automobile tracking: Make, Model, Year, VIN, Mileage, and depreciation.
  - Antiques, fine art, luxury watches, jewelry, and collectibles with condition grades, provenance, and insurance policy tracking.
  - Historical appraisal and valuation logs over time.

* **Goals, Budgets & Cashflow**:
  - Financial Goals & Sinking Funds with visual Kanban cards and required monthly savings targets.
  - Visual Category Budgets with `% Spent` progress bar gauges and custom payday cycle start days.
  - Scheduled bills and recurring outflow detector with 1-click bill schedule generation.
  - 90-Day cashflow balance forecaster (30d / 60d / 90d projected balances).

* **Advanced Financial Engines**:
  - Loan & Mortgage Amortization engine with extra principal prepayments and total interest/time saved calculations.
  - Monte Carlo Retirement Simulator with 1,000 stochastic geometric simulations (P10/P50/P90 percentiles).
  - Emergency digital estate access protocol with trusted contacts and security waiting periods.
  - Receipt and invoice image/PDF attachment previews.

* **Sure-Inspired Executive Wealth Dashboard**:
  - Modern card-based command center with Net Worth, Cashflow, Portfolio, and Real Estate Equity.
  - Full Balance Sheet breakdown: Assets (Cash, Stocks, Properties) vs. Liabilities (Cards, Loans, Mortgages).
  - Financial Runway (months of survival) and FIRE 4% rule progress bar.
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
        'views/insight_views.xml',
        'views/ai_advisor_views.xml',
        'views/ai_receipt_views.xml',
        'views/portfolio_analytics_views.xml',
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
