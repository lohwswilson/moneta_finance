# Moneta Personal Finance for Odoo 18

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-purple.svg)](https://www.odoo.com)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)

**Moneta Personal Finance** is a full-featured personal wealth, budgeting, and investment operating system built natively for **Odoo 18** (combining the best features of *Quicken Personal Finance Premier*, *Monize*, and *Sure / Maybe Finance*).

It provides complete multi-account tracking, running balance checkbook registers, 1-click status toggles, split transactions, category budgets with payday cycles, scheduled bills, stock portfolio management with average-cost accounting, dual-momentum strategies (GEM), loan amortization with prepayment savings, 1,000-path Monte Carlo wealth simulations, real estate home equity tracking, financial goals, automated rule engine, and FIRE / runway analytics.

---

## 🌟 Comprehensive Feature Suite

### 1. 🏦 Banking & Checkbook Registers (Quicken Premier Style)
- **Checkbook Register** with real-time cumulative running balances.
- **1-Click `Clr` Toggle** directly on list rows (*Unreconciled $\rightarrow$ Cleared $\rightarrow$ Reconciled*).
- **Payee QuickFill**: Automatically populates Category, Amount, Memo, and Tags based on past history.
- **Multi-Line Split Transactions**: Itemized categorization with sum validation.
- **Bank Statement Reconciliation Wizard**: Interactive matching with live $0.00 difference target.
- **QIF, OFX, and CSV Imports**: Automatic column mapping and wildcard payee matching.
- **Checkbook Register Export**: 1-click export to standard QIF or CSV.

### 2. 📈 Investments & Portfolio Management
- **Ticker Master & Daily Quotes**: Multi-lot holdings with average cost basis.
- **Realized & Unrealized Capital Gains**: Live return $\%$ calculations and cost basis tracking.
- **Global Equities Momentum (GEM)**: 12-month dual-momentum asset allocation rule and signal generator.
- **Multi-Asset Allocation Pie Charts**: Target vs. actual portfolio weighting.

### 3. 🎯 Goals, Budgets & Cashflow
- **Financial Goals & Sinking Funds**: Target amounts and dates, required monthly savings ($\frac{\text{Target}-\text{Saved}}{\text{Months}}$), and Kanban progress cards.
- **Category Budgets**: Visual `% Spent` progress bar gauges with custom payday cycle start days (e.g. 15th-to-14th).
- **Scheduled Bills & Reminders**: Overdue, Due Today, and Due in 7 Days badges with 1-click Post / Skip.
- **Smart Subscription Detector**: Analyzes transaction cadence to uncover recurring SaaS/streaming charges.

### 4. 🏡 Real Estate, Loans & Wealth Simulator
- **Real Estate & Home Equity Tracker**: Property appraisal tracking, mortgage debt linkage, net home equity ($), and LTV $\%$.
- **Loan & Mortgage Amortization Engine**: Prepayment scenarios, month-by-month principal/interest schedules, and total interest/time saved metrics.
- **Monte Carlo Retirement Simulator**: 1,000 stochastic geometric simulations with plan success probability ($\%$) and $P_{10}/P_{50}/P_{90}$ trajectory percentiles.
- **Emergency Digital Estate Access**: Trusted emergency contacts with configurable security waiting periods.

### 5. 💎 Executive Wealth Dashboard (Sure.am Style)
- **4 KPI Hero Cards**: Net Worth, Monthly Cashflow, Investment Portfolio, and Real Estate Equity.
- **Balance Sheet Breakdown**: Detailed split of Assets (*Cash, Stocks, Properties*) vs. Debt (*Cards, Mortgages, Loans*).
- **FIRE & Financial Runway**: Exact survival runway in months and 4% safe withdrawal rule milestone progress bar.
- **Quick Action Launchpad**: 1-click navigation across all 10 modules.

---

## 🚀 Installation & Setup

### 1. Clone the Module
```bash
cd /path/to/your/custom_addons
git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git
```

### 2. Install in Odoo
```bash
./odoo-bin -c odoo.conf -d <your_database> -i moneta_finance
```
Or upgrade an existing database:
```bash
./odoo-bin -c odoo.conf -d <your_database> -u moneta_finance
```

---

## 🧪 Automated Test Suite

Run the full automated test suite covering all modules, balance mathematics, record rules, loan amortization, and Monte Carlo engines:

```bash
./odoo-bin -c odoo.conf -d <your_database> -u moneta_finance \
  --test-enable --test-tags=moneta_finance --stop-after-init
```

---

## 📄 License

This project is licensed under the [GNU Lesser General Public License v3.0 (LGPL-3)](LICENSE).
