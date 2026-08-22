# Moneta Personal Finance for Odoo 18

<div align="center">

![Moneta Banner](https://img.shields.io/badge/Odoo-18.0-purple.svg?style=for-the-badge&logo=odoo)
![License](https://img.shields.io/badge/License-LGPL_v3-blue.svg?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg?style=for-the-badge&logo=python)
![Market Quotes](https://img.shields.io/badge/Market%20Quotes-Yahoo%20Finance-0284c7.svg?style=for-the-badge&logo=yahoo)

**An Open-Source Personal Finance, Banking & Wealth Management Suite for Odoo 18.**

*Combining the financial depth of Quicken Premier, the behavioral discipline of YNAB, the visual elegance of Monarch & Copilot, and the sovereign privacy of Odoo.*

</div>

---

## 🌟 Executive Overview

**Moneta Personal Finance** is a 100% self-hosted, sovereign personal finance and wealth management platform built on the enterprise-grade **Odoo 18** ORM and PostgreSQL backend.

Unlike closed cloud SaaS applications (Mint, Monarch, YNAB) that lock your financial history behind monthly subscriptions, Moneta runs entirely on your own private infrastructure with **zero cloud data broker tracking**, **native real-time multi-currency support**, and **direct local AI / MCP agent integration**.

```mermaid
graph TD
    subgraph Moneta Modular Architecture
        Core[<b>moneta_finance (Core Engine)</b><br/>Multi-Currency | Checkbook Ledger | Yahoo Quotes | Tax Lots]
        Prop[<b>moneta_finance_property</b><br/>Real Estate | Landlord Rent Roll | Tenant Leases]
        SG[<b>moneta_finance_singapore</b><br/>CPF 4-Accounts | SRS | HDB Loans | SSB & IRAS]
        MY[<b>moneta_finance_malaysia</b><br/>EPF 3-Accounts | LHDN Borang BE | Flexi-Loan SBR]
        AI[<b>moneta_finance_ai_advisor</b><br/>Local Ollama LLMs | MCP Server | Audit Insights]
        
        Core --> Prop
        Core --> SG
        Core --> MY
        Core --> AI
    end
```

---

## 📚 Complete Documentation Library

Explore the complete guides across all personal finance domains:

<div class="grid cards" markdown>

-   :material-rocket-launch: **[1. Getting Started & Setup](01_GETTING_STARTED.md)**
    
    ---
    System prerequisites, 30-second Docker setup, native Odoo 18 installation, and base currency configuration.

-   :material-bank: **[2. Banking & Checkbook Registers](02_BANKING_AND_RECONCILIATION.md)**
    
    ---
    Quicken-style running balances, 1-click `Clr` toggles, split transactions, and bank statement reconciliation wizards.

-   :material-chart-line: **[3. Stocks & Investment Center](03_STOCKS_AND_INVESTMENTS.md)**
    
    ---
    Live Yahoo Finance hourly quote sync, multi-lot average cost basis, corporate actions, and dividend tracking.

-   :material-bullseye-arrow: **[4. Budgets, Bills & Subscriptions](04_BUDGETS_BILLS_AND_SUBSCRIPTIONS.md)**
    
    ---
    Payday envelope budgeting, 14-day bill reminder horizons, and AI subscription price creep detection.

-   :material-home-city: **[5. Real Estate & Loan Amortization](05_REAL_ESTATE_AND_AMORTIZATION.md)**
    
    ---
    Property appraisal tracking, net home equity, mortgage debt metrics, and loan prepayment savings simulators.

-   :material-fire: **[6. FIRE & Wealth Simulator](06_FIRE_AND_SIMULATION.md)**
    
    ---
    Emergency liquid cash runway, Trinity 4% rule FIRE milestones, and 1,000-path stochastic Monte Carlo simulations.

-   :material-shield-lock: **[7. Security & Household Privacy](07_SECURITY_AND_MULTI_USER.md)**
    
    ---
    Record-level user isolation, joint family account sharing, and time-delayed digital estate emergency access.

-   :material-flag-checkered: **[8. Singapore & SEA Wealth](09_SINGAPORE_AND_SEA_WEALTH.md)**
    
    ---
    CPF (OA/SA/MA/RA), CPF LIFE simulator, SRS tax optimization, HDB loans, SORA mortgages, SSB, and MAS T-Bills.

-   :material-palm-tree: **[9. Malaysia Wealth & Tax Pack](10_MALAYSIA_WEALTH_AND_TAX.md)**
    
    ---
    EPF/KWSP 3-Account restructuring, LHDN Borang BE Tax Relief Planner, PRS, ASNB Unit Trusts, and Semi-Flexi Loans.

-   :material-code-braces: **[10. Developer Architecture & MCP](08_DEVELOPER_AND_API.md)**
    
    ---
    Entity relationship diagrams (ERD), automated cron jobs, custom dashboard launchpad actions, and testing.

</div>

---

## ⚡ 30-Second Quickstart (Docker)

```bash
git clone https://github.com/lohwswilson/moneta_finance.git
cd moneta_finance
docker compose up -d
```

Access Odoo at `http://localhost:8069` (login: `admin` / `admin`).
