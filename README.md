# Moneta Personal Finance for Odoo 18

<div align="center">

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-purple.svg?style=for-the-badge&logo=odoo)](https://www.odoo.com)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg?style=for-the-badge)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Live Market Quotes](https://img.shields.io/badge/Market%20Quotes-Yahoo%20Finance-0284c7.svg?style=for-the-badge&logo=yahoo)](https://finance.yahoo.com)
[![CI / Test Suite](https://github.com/lohwswilson/moneta_finance/actions/workflows/ci.yml/badge.svg?branch=18.0)](https://github.com/lohwswilson/moneta_finance/actions)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)

**An Open-Source Personal Finance, Banking & Wealth Management Module for Odoo 18.**

*Combining the financial depth of Quicken Premier, the modern design of Maybe & Copilot Money, and the enterprise power of Odoo.*

[Explore Documentation](docs/01_GETTING_STARTED.md) · [View Roadmap](ROADMAP.md) · [Report Bug](https://github.com/lohwswilson/moneta_finance/issues) · [Request Feature](https://github.com/lohwswilson/moneta_finance/issues)

</div>

---

## 🌟 Executive Highlights

* 💎 **Wealth Command Center**: Real-time Net Worth, multi-currency conversion, cash flow savings rate, and 4% FIRE milestone tracking.
* 🎴 **Color-Coded Accounts & Cards**: Visual 🟢 Emerald Green for Banks, 🔵 Royal Blue for Brokerage, 🟣 Royal Purple for Credit Cards, and 🔴 Crimson Red for Loans.
* 📈 **Quicken Premier Stock Portfolio**: Live Yahoo Finance real-time price updates, multi-lot holdings with average cost basis, auto-refresh cron, and gain/loss analytics.
* 📋 **Interactive Bank Reconciler**: Checkbook ledger with live running balances, 1-click `Clr` status toggles, split transactions, and statement reconciliation wizard.
* 🏡 **Real Estate & Home Equity**: Property valuations, mortgage linkage, loan prepayment simulators, and LTV metrics.
* 🤖 **AI Advisor & Smart Insights**: Automated financial health audits, cash flow leak detection, and actionable advisory recommendations.
* 🎲 **1,000-Path Monte Carlo Wealth Simulator**: Stochastic retirement projections with $P_{10}/P_{50}/P_{90}$ percentile bands.
* 🔒 **Multi-User Household Privacy**: Isolated records with granular joint account sharing and emergency digital estate access.

---

## 💡 Why This Module Exists

> *"Years ago, I was a dedicated user of **Microsoft Money**. It was reliable, simple, and gave me complete visibility over my personal finances. But after Microsoft discontinued it, I had to move to **Quicken**.*
>
> *Over time, commercial apps became either bloated, locked behind monthly subscriptions, or trapped in closed cloud platforms that didn't give me direct access to my data. Meanwhile, my finances were scattered across bank accounts, foreign stock brokers, and spreadsheets.*
>
> *Having worked with and developed on **Odoo** for several years, I realized: **Why not build a personal finance module inside Odoo?** Odoo already has the best multi-currency engine, robust ORM, and PostgreSQL backing—everything needed for solid checkbook registers and portfolio tracking.*
>
> *So one weekend, I sat down and built this module to bring back the clean checkbook experience of Microsoft Money right inside my Odoo environment.*
>
> *I've open-sourced this module so anyone running Odoo can easily manage their personal wealth and investments on their own database."*
>
> — **Wilson Loh** ([@lohwswilson](https://github.com/lohwswilson))

---

## ⚡ Quickstart (Choose One)

### Option A: 30-Second Docker Setup (Fastest)
```bash
git clone https://github.com/lohwswilson/moneta_finance.git
cd moneta_finance
docker compose up -d
```
Access Odoo at `http://localhost:8069` (login: `admin` / `admin`).

### Option B: Native Odoo 18 Addon
1. Install Python dependencies:
   ```bash
   pip install yfinance pandas numpy matplotlib
   ```
2. Clone into your Odoo addons path:
   ```bash
   cd /path/to/your/custom_addons
   git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git
   ```
3. Install or update the module in Odoo:
   ```bash
   ./odoo-bin -c odoo.conf -d <your_database> -i moneta_finance
   ```

---

## 📚 Complete Documentation Library

Explore our in-depth guides in the [`docs/`](docs/) directory:

| Guide | Description |
| :--- | :--- |
| 🚀 [**1. Getting Started & Onboarding**](docs/01_GETTING_STARTED.md) | Installation, base currency setup, creating accounts, CSV/QIF import |
| 🏦 [**2. Banking & Statement Reconciliation**](docs/02_BANKING_AND_RECONCILIATION.md) | Checkbook registers, 1-click `Clr` toggle, split transactions, matching wizard |
| 📈 [**3. Stocks & Investment Center**](docs/03_STOCKS_AND_INVESTMENTS.md) | Live Yahoo Finance quotes, average cost basis, multi-currency FX math |
| 🎯 [**4. Budgets, Bills & Subscriptions**](docs/04_BUDGETS_BILLS_AND_SUBSCRIPTIONS.md) | Payday envelope cycles, 14-day bill reminders, recurring charge detector |
| 🏡 [**5. Real Estate & Loan Amortization**](docs/05_REAL_ESTATE_AND_AMORTIZATION.md) | Property appraisals, net home equity, prepayment savings calculators |
| 🎲 [**6. FIRE Analytics & Wealth Simulator**](docs/06_FIRE_AND_SIMULATION.md) | Emergency runway buffer, 4% rule milestone, Monte Carlo 1,000-path engine |
| 🔒 [**7. Multi-User Privacy & Joint Sharing**](docs/07_SECURITY_AND_MULTI_USER.md) | User isolation, joint permission levels (`read`/`write`/`full`), emergency access |
| 🛠️ [**8. Developer Architecture & APIs**](docs/08_DEVELOPER_AND_API.md) | Data models (ERD), cron jobs, custom dashboard launchpad actions, testing |

---

## 🗺️ Product Roadmap & Future Features

We have an active product roadmap with exciting upcoming milestones:
* 🏦 **Phase 2**: Open Banking & Live Bank Sync (Plaid, Salt Edge, SimpleFIN)
* 📊 **Phase 3**: Global Tax Packs (Singapore CPF/IRAS, US 1099, UK HMRC)
* 🪙 **Phase 4**: Crypto Exchange API Sync & Commodities Tracking
* 📱 **Phase 5**: Mobile Progressive Web App (PWA) & Offline Expense Logging
* 🤖 **Phase 6**: Autonomous Financial Copilot & 90-Day Predictive Forecasting

Check out [`ROADMAP.md`](ROADMAP.md) to see the full vision and contribute!

---

## 🤝 Contributing & Community

We love contributions! Check out [`CONTRIBUTING.md`](CONTRIBUTING.md) to learn how to:
* Set up your local environment
* Follow our Conventional Commits convention
* Submit bug fixes and feature pull requests

Please also review our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 🧪 Automated Testing

Run the full automated test suite covering all modules, balance calculations, record rules, and financial algorithms:

```bash
./odoo-bin -c odoo.conf -d <your_database> -u moneta_finance \
  --test-enable --test-tags=moneta_finance --stop-after-init
```

---

## 📄 License

This module is licensed under the [GNU Lesser General Public License v3.0 (LGPL-3)](LICENSE).
