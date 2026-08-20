# Moneta Personal Finance - Product Roadmap & Community Backlog

This document outlines the strategic roadmap for **Moneta Personal Finance**. We welcome community contributions, architectural discussions, and feature proposals!

---

## 🌟 Roadmap Milestones

### Phase 1: Core Wealth & Portfolio Engine (Completed ✅)
- [x] Multi-account management (Cash, Brokerage, Credit Cards, Loans)
- [x] Quicken-style Checkbook registers with real-time running balances and chronological tiebreakers
- [x] 1-Click `Clr` status toggles & interactive bank statement reconciliation
- [x] Transfer reconciliation independence with atomic pair-wide VOID transitions
- [x] Live Yahoo Finance stock quote engine with hourly cron & 1-click refresh
- [x] Investment trade reconciliation status (`unreconciled` / `cleared` / `reconciled` / `void`)
- [x] Multi-lot average cost basis accounting & capital gains analytics
- [x] Expanded recurring transaction cadences (Triannual / Biennial)
- [x] Direct loan & mortgage summary metrics on account views and kanban cards
- [x] Sure-style Executive Wealth Dashboard with Light Sky Blue theme
- [x] FIRE 4% rule milestone & 1,000-path Monte Carlo wealth simulator
- [x] 8-Part comprehensive GitHub documentation library

---

### Phase 2: Monize Advanced Feature Parity Sprint (Active 🚀)
*Executing sequentially track-by-track:*

* **Track 2.1: Payee Brand Favicons & Visual Category Hierarchy (Completed ✅)**
  - [x] Payee website domain field and automated favicon resolution (Google / gstatic Favicon cache)
  - [x] Payee brand avatars in checkbook registers, compact lists, and kanban cards
  - [x] Category icon glyph inheritance (subcategories inherit parent icons and badges)

* **Track 2.2: Variable-Rate Mortgage & Rate Change Inference Engine (Completed ✅)**
  - [x] Step-detection algorithm ($\text{rate} = \frac{\text{interest}}{\text{balance}} \times 12$) on historical split loan transactions
  - [x] Automated rate inference wizard generating historical `moneta.loan.rate.change` records
  - [x] Dynamic amortization curves adapting to segmented variable rate histories

* **Track 2.3: Microsoft Money 75+ Investment & Portfolio Metrics (Completed ✅)**
  - [x] Dynamic market metrics on `moneta.security`: 52-Week High/Low, Day's Gain/Loss ($ & %), Beta, Day Volume
  - [x] Fundamental valuation metrics: P/E Ratio, Forward P/E, EPS, Market Capitalization, Dividend Yield %
  - [x] Multi-period holding return metrics: Day's Gain/Loss, Portfolio Weight %, 52W High/Low, P/E, Market Cap, Beta

* **Track 2.4: Action History & 1-Click Undo / Rollback Engine (Completed ✅)**
  - [x] Mutation audit logger for batch operations (statement imports, batch categorization, rule execution)
  - [x] 1-Click "Undo Last Action" wizard to cleanly revert batch imports or bulk changes

* **Track 2.5: Time-Delayed Emergency Digital Estate Access**
  - [ ] Time-delayed security lock with configurable grace period (7, 14, or 30 days)
  - [ ] Automated daily email reminder cron to owner before granting access to emergency contacts
  - [ ] Read-only view permissions for designated family members/executors

* **Track 2.6: Financial Assistant MCP Server (Model Context Protocol)**
  - [ ] Standardized MCP tool endpoints for local AI agents (Claude, Gemini, Antigravity)
  - [ ] Natural language tool suite: balance queries, spending categorization, bill forecasting, and loan simulations

---

### Phase 3: Singapore & South East Asia Financial Ecosystem (Flagship 🇸🇬 🌏)
*Comprehensive localization for Singapore and South East Asian wealth structures:*

* **Track 3.1: CPF (OA/SA/MA/RA) & SRS Pension Architecture**
  - [ ] Specialized account types: `cpf_oa` (2.5%), `cpf_sa` (4.0%), `cpf_ma` (4.0%), `cpf_ra` (4.0%), and `srs`
  - [ ] Monthly CPF interest calculation engine (lowest balance rule) with annual December crediting
  - [ ] CPF LIFE retirement payout simulator (Standard, Escalating, Basic) with BRS / FRS / ERS threshold milestones
  - [ ] SRS voluntary tax-relief contributions ($15,300 citizen/PR, $35,700 foreigner) & 10-year penalty-free withdrawal tracker

* **Track 3.2: Singapore Housing, HDB Loans & CPF Accrued Interest**
  - [ ] CPF Housing Accrued Interest engine: calculates the 2.5% compounded interest liability due back to CPF upon property sale
  - [ ] HDB Concessionary Loan (pegged at CPF OA + 0.1% = 2.60%) & SORA-pegged commercial bank mortgage amortization
  - [ ] Buyer's Stamp Duty (BSD) & Additional Buyer's Stamp Duty (ABSD) property calculator (Singapore Citizen vs PR vs Foreigner)
  - [ ] Total Debt Servicing Ratio (TDSR $\le 55\%$) and Mortgage Servicing Ratio (MSR $\le 30\%$) affordability checks

* **Track 3.3: Singapore Savings Bonds (SSB), MAS T-Bills & S-REITs**
  - [ ] Singapore Savings Bonds (SSB) engine: 10-year step-up interest schedule with monthly par redemption ($100) and $2 MAS fee
  - [ ] MAS Treasury Bills (6-Month / 1-Year T-Bills) discount auction yield accounting
  - [ ] SGX (`.SI`) security master with one-tier tax-exempt dividend distribution handling and S-REIT distribution yield tracking
  - [ ] Irish-domiciled ETF tracking (`CSPX.L`, `VWRA.L`, `SWRD.L`) with 15% US dividend tax withholding advantage

* **Track 3.4: IRAS Tax Relief & Optimization Engine**
  - [ ] IRAS progressive personal income tax brackets with instant liability estimation
  - [ ] Tax Relief Tracker: Retirement Sum Topping-Up (RSTU $8k self + $8k loved ones), SRS ($15.3k), CPF Employee, NSman, Parent, and Child reliefs
  - [ ] Year-end tax optimization advisory: actionable suggestions to maximize tax deductions before Dec 31

* **Track 3.5: Pre-Configured Singapore / SEA Master Data**
  - [ ] Pre-loaded Singapore & SEA financial institutions: DBS/POSB, OCBC, UOB, Standard Chartered, MariBank, GXS, Trust Bank, CPF Board, Endowus, Syfe, Moomoo, Tiger Brokers, Maybank, CIMB
  - [ ] Pre-loaded common payees & categories: NTUC FairPrice, Cold Storage, Sheng Siong, Grab/GrabFood, Singtel, StarHub, M1, SP Group, HDB Town Council, IRAS, LTA SimplyGo/ERP, Shopee, Lazada

---

### Phase 4: Open Banking & Live Bank Sync (Q4 2026)
- [ ] **Plaid Integration**: US & Canada automated bank transaction download
- [ ] **Salt Edge / Teller / SimpleFIN Sync**: European & Global Open Banking live feed
- [ ] **Automated Rule Matching**: Auto-assign categories based on imported transaction metadata

---

### Phase 5: Global Tax & Multi-Jurisdiction Packs (Q1 2027)
- [ ] **US Tax Pack**: 1099-DIV, 1099-B capital gains schedule, and tax-loss harvesting
- [ ] **UK / EU Tax Pack**: Capital Gains Tax allowance tracking and ISA portfolio accounts
- [ ] **Malaysia / Regional Tax Pack**: EPF (KWSP) dividend tracking and LHDN tax relief schedule

---

### Phase 6: Crypto & Multi-Asset Hub (Q2 2027)
- [ ] **Crypto Exchange API Sync**: Read-only balance sync for Coinbase, Binance, and Kraken
- [ ] **On-Chain Wallet Tracking**: Ethereum, Bitcoin, and Solana public address balance monitoring
- [ ] **Commodities & Precious Metals**: Live Gold (XAU) and Silver (XAG) spot pricing

---

### Phase 7: Mobile PWA & Offline Experience (Q3 2027)
- [ ] **Responsive Mobile App**: Dedicated mobile-optimized dashboard view
- [ ] **Offline Quick-Receipt Entry**: Progressive Web App (PWA) offline expense logging

---

### Phase 8: Autonomous AI Financial Copilot (Q4 2027)
- [ ] **Autonomous Spending Leak Audits**: LLM-driven anomaly detection
- [ ] **Cash Flow Forecasting**: 90-day predictive balance forecast using seasonal regression
- [ ] **Subscription Negotiation Assistant**: Automated drafts for cancelling unused SaaS subscriptions

---

## 💡 How to Champion a Feature
If you'd like to work on any item from this roadmap:
1. Check the [Issues tab](https://github.com/lohwswilson/moneta_finance/issues) or open a new Proposal Issue.
2. Discuss the design approach with maintainers.
3. Submit a Pull Request targeting branch `18.0`.
