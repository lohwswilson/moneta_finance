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
*Closing advanced feature gaps from Microsoft Money and Monize (`/opt/monize`):*

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

* **Track 2.5: Time-Delayed Emergency Digital Estate Access (Completed ✅)**
  - [x] Time-delayed security lock with configurable grace period (7, 14, or 30 days)
  - [x] Automated daily email reminder cron to owner before granting access to emergency contacts
  - [x] Read-only view permissions for designated family members/executors

* **Track 2.6: Financial Assistant MCP Server (Model Context Protocol) (Completed ✅)**
  - [x] Standardized MCP tool endpoints for local AI agents (Claude, Gemini, Antigravity)
  - [x] Natural language tool suite: balance queries, spending categorization, bill forecasting, and loan simulations

* **Track 2.7: Direct Microsoft Money (`.mny`) Native Binary Importer**
  - [ ] Native binary `.mny` parser wizard (`wizards/mny_import_wizard.py`) extracting accounts, transfers, multi-line splits, investment transactions (Buy, Sell, Reinvest, Split), historical price series, scheduled bills, and custom exchange rates without intermediate QIF export
  - [ ] Automated post-import reconciliation audit verifying balance and holding integrity against the source `.mny` database

* **Track 2.8: Scoped Personal Access Token (PAT) Management for MCP & API**
  - [ ] Dedicated UI in Moneta Configuration to generate, label, expire, and revoke scoped API/MCP tokens
  - [ ] Granular permission scopes (`read:ledger`, `write:transactions`, `read:reports`, `read:investments`, `admin`) for external autonomous AI agents

* **Track 2.9: Automated User-Scoped Snapshot Backups (`.json.gz`) & 1-Click Restore**
  - [ ] Scheduled background cron generating daily, weekly, and monthly `.json.gz` self-contained data archives sharded per user
  - [ ] Automated retention pruning policy (e.g. keep 7 daily, 4 weekly, 12 monthly archives)
  - [ ] 1-Click user data download and restore wizard directly from user preferences

* **Track 2.10: Financial Data Reset & Re-Import Wizard**
  - [ ] Safe 1-click purge wizard to wipe all financial transactions, accounts, and securities while strictly preserving user credentials, system settings, custom categories, and tags

---

### Phase 3: Singapore & South East Asia Financial Ecosystem (Flagship 🇸🇬 🌏)
*Comprehensive localization for Singapore and South East Asian wealth structures:*

* **Track 3.1: CPF (OA/SA/MA/RA) & SRS Pension Architecture (Completed ✅)**
  - [x] Specialized account types: `cpf_oa` (2.5%), `cpf_sa` (4.0%), `cpf_ma` (4.0%), `cpf_ra` (4.0%), and `srs`
  - [x] Monthly CPF interest calculation engine (lowest balance rule) with annual December crediting
  - [x] CPF LIFE retirement payout simulator (Standard, Escalating, Basic) with BRS / FRS / ERS threshold milestones
  - [x] SRS voluntary tax-relief contributions ($15,300 citizen/PR, $35,700 foreigner) & 10-year penalty-free withdrawal tracker

* **Track 3.2: Singapore Housing, HDB Loans & CPF Accrued Interest (Completed ✅)**
  - [x] CPF Housing Accrued Interest engine: calculates the 2.5% compounded interest liability due back to CPF upon property sale
  - [x] HDB Concessionary Loan (pegged at CPF OA + 0.1% = 2.60%) & SORA-pegged commercial bank mortgage amortization
  - [x] Buyer's Stamp Duty (BSD) & Additional Buyer's Stamp Duty (ABSD) property calculator (Singapore Citizen vs PR vs Foreigner)
  - [x] Total Debt Servicing Ratio (TDSR $\le 55\%$) and Mortgage Servicing Ratio (MSR $\le 30\%$) affordability checks

* **Track 3.3: Singapore Savings Bonds (SSB), MAS T-Bills & S-REITs (Completed ✅)**
  - [x] Singapore Savings Bonds (SSB) engine: 10-year step-up interest schedule with monthly par redemption ($100) and $2 MAS fee
  - [x] MAS Treasury Bills (6-Month / 1-Year T-Bills) discount auction yield accounting
  - [x] SGX (`.SI`) security master with one-tier tax-exempt dividend distribution handling and S-REIT distribution yield tracking
  - [x] Irish-domiciled ETF tracking (`CSPX.L`, `VWRA.L`, `SWRD.L`) with 15% US dividend tax withholding advantage

* **Track 3.4: IRAS Tax Relief & Optimization Engine (Completed ✅)**
  - [x] IRAS progressive personal income tax brackets with instant liability estimation
  - [x] Tax Relief Tracker: Retirement Sum Topping-Up (RSTU $8k self + $8k loved ones), SRS ($15.3k), CPF Employee, NSman, Parent, and Child reliefs
  - [x] Year-end tax optimization advisory: actionable suggestions to maximize tax deductions before Dec 31

* **Track 3.5: Pre-Configured Singapore / SEA Master Data (Completed ✅)**
  - [x] Pre-loaded Singapore & SEA financial institutions: DBS/POSB, OCBC, UOB, Standard Chartered, MariBank, GXS, Trust Bank, CPF Board, Endowus, Syfe, Moomoo, Tiger Brokers, Maybank, CIMB
  - [x] Pre-loaded common payees & categories: NTUC FairPrice, Cold Storage, Sheng Siong, Grab/GrabFood, Singtel, StarHub, M1, SP Group, HDB Town Council, IRAS, LTA SimplyGo/ERP, Shopee, Lazada

---

### Phase 4: Quicken Classic Power Parity & Landlord Hub (Completed ✅)
*Closing the core functional gaps with Quicken Classic Premier & Home & Business:*

* **Track 4.1: Interactive Cash Flow & Financial Calendar View (Completed ✅)**
  - [x] Month/Week/Day visual calendar view (`view_mode="calendar"`) plotting scheduled bills, deposits, and transfers
  - [x] Daily projected end-of-day bank balance calculation across all active checking/savings accounts
  - [x] Visual overdraft & low-balance threshold warnings on future calendar dates
  - [x] 1-Click quick-entry and skip occurrence directly from the interactive calendar view

* **Track 4.2: Investment Tax-Lot Accounting (Specific ID, FIFO, LIFO, HIFO) (Completed ✅)**
  - [x] Lot-level purchase tracking (`moneta.security.lot`) recording purchase date, quantity, cost basis, and remaining shares
  - [x] Automated disposal strategies on stock/ETF sells: **FIFO**, **LIFO**, **HIFO** (Highest In, First Out), and **Specific Identification**
  - [x] Holding period tracking ($< 365$ days vs. $\ge 365$ days) for Short-Term vs. Long-Term Capital Gains classification
  - [x] Tax-loss harvesting opportunities analyzer with lot-level capital gain/loss breakdown

* **Track 4.3: Landlord & Rental Property Lease / Tenant Roll (`moneta_finance_property`) (Completed ✅)**
  - [x] Tenant management (`moneta.property.tenant`) with lease start/end dates, monthly rent amount, and security deposit tracking
  - [x] Rent roll ledger with automated monthly rent invoice generation and overdue rent alerts
  - [x] Rental property expense categorization and Schedule E net operating income (NOI) reporting

* **Track 4.4: Tax Schedule & TurboTax TXF Export (Completed ✅)**
  - [x] IRS Form 8949 / Schedule D capital gains summary report generator
  - [x] 1099-DIV / 1099-INT dividend and interest income tax schedules
  - [x] Standard `.txf` (Tax Exchange Format) file exporter for 1-click import into TurboTax, TaxSlayer, and H&R Block

---

### Phase 5: Monarch Modern Experience & Collaborative Cash Flow (Q1 2027)
*Incorporating modern cash flow visualizers, flexible household workflows, and forward-looking forecasting inspired by Monarch Money:*

* **Track 5.1: Interactive Cash Flow Sankey Diagram & Visual Wealth Velocity**
  - [ ] Interactive D3.js / Chart.js Sankey visualizer widget in Odoo 18 OWL dashboard (`moneta.dashboard`)
  - [ ] Multi-stage dynamic flow: Income Streams $\rightarrow$ Master Groups (Fixed, Variable, Savings) $\rightarrow$ Detailed Categories $\rightarrow$ Net Savings & Investments
  - [ ] Interactive period filtering (Current Month, Last Month, Quarter-to-Date, Year-to-Date, Custom Date Range)
  - [ ] 1-Click node drill-down: Clicking any Sankey node opens the filtered checkbook ledger for those underlying transactions
  - [ ] Gross vs. Net Cash Flow toggle (including/excluding internal transfers and credit card settlements)

* **Track 5.2: 12-Month Forward Cash Flow & "What-If" Scenario Forecaster (`moneta.cashflow.forecast`)**
  - [ ] Deterministic forward balance projection engine combining `moneta.recurring` scheduled cadences and active `moneta.budget` allocations
  - [ ] Projected daily and monthly account balance trajectory curve across all liquid checking and savings accounts
  - [ ] Low-balance and overdraft risk warning flags with projected breach dates
  - [ ] Interactive "What-If" scenario sandbox: simulate financial milestones (e.g. car purchase, bonus payout, sabbatical, home down payment) without modifying actual ledger records
  - [ ] Scenario comparison view: baseline trajectory vs. alternative scenario net worth and liquidity curves

* **Track 5.3: Collaborative "Needs Review" Inbox & Household Transaction Triage**
  - [ ] Transaction review lifecycle state (`needs_review`, `reviewed`) on `moneta.transaction`
  - [ ] Dedicated "Needs Review" badge counter and quick filter on the checkbook ledger and dashboard
  - [ ] Household member assignment (`assigned_user_id`) to allocate transactions for partner verification
  - [ ] In-line discussion chatter (`mail.thread`) enabling comments, questions (e.g. "Did you buy this?"), and internal notes per transaction
  - [ ] 1-Click batch "Mark as Reviewed" action wizard

* **Track 5.4: Flexible Category-Group Budgeting & Per-Category Rollovers**
  - [ ] High-level Group Budgeting: set budgets at the master category group level (e.g. "Discretionary Spending", "Lifestyle", "Fixed Bills") with automatic subcategory rollup
  - [ ] Granular Per-Category Rollover toggle: independently enable/disable rollover balances on a per-category basis (`is_rollover`)
  - [ ] Flexible Budget Switcher: toggle between Detailed Category View, Group Summary View, and 50/30/20 Rule View
  - [ ] Real-time visual progress bars with overspending alerts and pace indicators (e.g. "12 days left, 45% budget remaining")

* **Track 5.5: Advanced Multi-Condition Rule Engine with Regex & Auto-Splits**
  - [ ] Regex and raw bank description pattern matching on `moneta.transaction.rule`
  - [ ] Multi-criteria condition builder: `Raw Memo (Regex)` + `Amount Range` + `Account Scope` + `Date Range`
  - [ ] Multi-action execution: `Rename Standard Payee`, `Assign Category & Tags`, `Set Status`, `Hide from Budget / Reports`
  - [ ] Automated Split Templates: auto-split matched transactions by percentage (e.g. 50% Personal / 50% Reimbursable) or fixed dollar amounts
  - [ ] Interactive Rule Dry-Run & Testing wizard before saving, with 1-click retroactive batch execution

* **Track 5.6: Budget-Linked Goals & Virtual Multi-Account Sinking Funds**
  - [ ] Multi-account goal funding: link a single savings goal across multiple bank accounts or dedicate a fractional slice of a high-yield account
  - [ ] Dynamic Budget Integration: auto-inject required monthly goal contributions (`monthly_contribution_required`) as first-class line items into `moneta.budget`
  - [ ] Goal priority tiering (Priority 1: Emergency Fund $\rightarrow$ Priority 2: Mortgage Down Payment $\rightarrow$ Priority 3: Travel)
  - [ ] Visual goal completion milestone forecaster calculating estimated achievement date based on trailing 3-month savings velocity

* **Track 5.7: Subscription "Price Creep" & Amount Variance Detector**
  - [ ] Statistical baseline price tracking on detected subscriptions in `moneta.subscription.detector`
  - [ ] Automated price creep alerts whenever an imported recurring charge increases by $>5\%$ or exceeds historical median
  - [ ] Dedicated "Subscription Health & Price Creep" audit card on the Executive Dashboard
  - [ ] Price change history log per recurring subscription payee showing historical price hikes over time

* **Track 5.8: Modular Drag-and-Drop Customizable OWL Dashboard**
  - [ ] User-configurable widget layout engine in Odoo 18 OWL dashboard (`moneta.dashboard`)
  - [ ] Customizable card arrangement: drag-and-drop reordering, column resizing, and toggling visibility of dashboard widgets
  - [ ] Available widget catalog: Net Worth Curve, Cash Flow Sankey Preview, Recent Transactions, Needs Review Inbox, Budget vs. Actual, Recurring Billing Calendar, Goals Tracker, and Investment Watchlist
  - [ ] Per-user layout persistence stored in user preferences (`moneta.dashboard.config`)

---

### Phase 6: YNAB Zero-Based Envelope Budgeting & Cash Allocation Engine (Q1 2027)
*Delivering strict zero-based envelope budgeting, cash guardrails, and dynamic money movement inspired by YNAB:*

* **Track 6.1: Zero-Based "Ready to Assign" (RTA) Cash Guardrail & Banner**
  - [ ] Real-time liquid cash calculation: $\text{Ready to Assign} = \text{Total Checking/Savings Cash} - \sum \text{Allocated Envelopes}$
  - [ ] Visual top banner on Budget Period view displaying RTA status (Green when $0.00, Yellow when positive cash unassigned, Red when over-allocated)
  - [ ] Strict cash guardrail mode: prevents budgeting unreceived/projected income to enforce true cash-on-hand discipline
  - [ ] Payday income intake pipeline auto-incrementing RTA balance on bank deposit

* **Track 6.2: Automated Credit Card Payment Reserve & Shift Engine**
  - [ ] Automated cash envelope shift on credit card spending: moving available funds from budgeted category (e.g. Groceries) directly into dedicated Credit Card Payment reserve category
  - [ ] "Available for Payment" vs. "Credit Card Statement Balance" reconciliation indicator (Green = Paid-in-Full, Yellow/Red = Carrying Balance / Debt)
  - [ ] Credit card payment transfer wizard paying statement balance from reserved funds without affecting expense categories
  - [ ] Credit card debt paydown goal simulator for users carrying revolving debt

* **Track 6.3: Smart Dynamic Target Types ("Needed for Spending", "Target by Date", "Monthly Builder")**
  - [ ] Target type configuration on `moneta.budget.category`:
    - **Needed for Spending (Monthly Refill)**: Sets monthly spending ceiling, automatically deducting rollover surplus from required monthly funding ($\text{Needed} = \text{Target} - \text{Rollover}$)
    - **Target Balance by Date (Sinking Fund)**: Automatically computes monthly required contribution based on remaining months until target date ($\text{Monthly} = \frac{\text{Target} - \text{Current}}{\text{Months Remaining}}$)
    - **Monthly Savings Builder**: Fixed monthly allocation regardless of account balance
  - [ ] Auto-calculation of `underfunded_amount` across all categories for the active period

* **Track 6.4: "Roll with the Punches" 1-Click Overspending Resolution Wizard (`moneta.budget.cover.wizard`)**
  - [ ] Visual overspending alert: highlighted red badge on overspent categories ($< 0.00$)
  - [ ] Interactive 1-Click "Cover Overspending" modal listing categories with surplus available funds
  - [ ] Instant intra-period fund reallocation with mutation audit logging in `moneta.action.history`
  - [ ] Automated end-of-period overspending cleanup options (deduct from next month's RTA vs. absorb into debt)

* **Track 6.5: "Age of Money" (AOM) & Days of Cash Buffer Engine**
  - [ ] FIFO (First-In, First-Out) cash queue engine matching outgoing transaction payments against historical deposit dates
  - [ ] Real-time "Age of Money" (AOM) metric on the Executive Dashboard ($< 30\text{ days}$ Paycheck-to-paycheck vs. $\ge 30\text{ days}$ Living on last month's income)
  - [ ] "Days of Buffer" metric estimating how many days current liquid cash would sustain average historical spending velocity without new income
  - [ ] Historical 12-month AOM progression chart

* **Track 6.6: 1-Click "Auto-Assign" / Quick Budget Engine**
  - [ ] 1-Click "Auto-Assign" action button on budget period with selectable distribution strategies:
    - **Underfunded**: Fully funds all active category targets up to their calculated shortfall
    - **Assigned Last Month**: Duplicates exact category assignments from the preceding month
    - **Average Spent**: Allocates funds based on trailing 3-month average actual category spending
    - **Custom Priority Allocation**: Distributes available RTA funds down category priority tiers until RTA reaches $0.00

---

### Phase 7: Open Banking & Automated Feed Sync (Q1 2027)
- [ ] **Plaid Integration**: US & Canada automated bank transaction download and account balance refresh
- [ ] **Salt Edge / Teller / SimpleFIN Sync**: European & Global Open Banking live feed integration
- [ ] **Automated Rule Matching Engine**: Auto-assign categories, payees, and split templates based on imported bank metadata and regex patterns
- [ ] **Bank Feed Deduplication**: Fuzzy hash matching against pending manual entries to prevent double-counting

---

### Phase 8: Global Tax & Multi-Jurisdiction Packs
- [x] **US Tax Pack (Completed ✅)**: Form 8949, Schedule D, 1099-DIV/INT, Schedule E, and TurboTax `.txf` export
- [x] **Malaysia Wealth & Tax Pack (`moneta_finance_malaysia`) (Completed ✅)**:
  - [x] EPF / KWSP 3-Account Hub (Akaun Persaraan 75%, Sejahtera 15%, Fleksibel 10%, dividend compounding, and i-Saraan matching)
  - [x] LHDN Borang BE Tax Relief Planner & Optimizer (Individual, Medical, Lifestyle, Sports, SSPN, EPF, Life, PRS, EV charging)
  - [x] Private Retirement Scheme (PRS) & ASNB Unit Trusts (ASB/ASM capital protected fixed-price tracking)
  - [x] Malaysian Semi/Full-Flexi Housing Loan SBR interest savings simulator
  - [x] RPGT (Real Property Gains Tax) disposal capital gains tax calculator
  - [x] Pre-loaded Malaysian banks, digital banks (GXBank, Boost Bank, AEON Bank), e-wallets, and utility payees
- [ ] **UK / EU Tax Pack**: Capital Gains Tax (CGT) annual exempt amount tracking, ISA (Individual Savings Account) wrapper management, and HMRC Self Assessment schedules

---

### Phase 9: Multi-Market Stock Intelligence, Technical Indicators & Strategies (Q2-Q3 2027)
*Incorporating technical indicator engines and strategy scanners from `daily_stock_analysis` (`/opt/daily_stock_analysis`):*

* **Track 9.1: Multi-Market Historical & Real-Time Data Pipeline**
  - [ ] Expanded market data fetchers with fallback hierarchy: **Yahoo Finance**, **AkShare**, **Tushare**, **TickFlow**, **Longbridge**, and **AlphaVantage**
  - [ ] Multi-market support: US (NYSE, NASDAQ), HK (HKEX), China A-Shares (SSE, SZSE, BSE), Singapore (SGX), Malaysia (Bursa), Japan (TSE), South Korea (KRX), Taiwan (TWSE), and Global ETFs
  - [ ] Automated market trading calendar awareness (auto-skip holidays across US, SG, MY, HK, and CN exchanges)

* **Track 9.2: Technical Indicator Calculation Engine (`moneta.security.price`)**
  - [ ] **Moving Averages**: MA5, MA10, MA20, MA50, MA60, MA120, MA250, EMA12, EMA26
  - [ ] **Momentum & Trend Oscillators**: MACD (DIF, DEA, Histogram), RSI (6, 12, 24 periods with overbought/oversold bands), KDJ (9, 3, 3)
  - [ ] **Volatility & Range**: Bollinger Bands (20-day, $\pm 2\sigma$, Bandwidth %), Average True Range (ATR 14)
  - [ ] **Volume & Liquidity Metrics**: Volume Ratio (量比), Volume Spike factor ($>2\times$ 20-day average volume), VWAP (Volume Weighted Average Price)
  - [ ] **Chip Distribution Analytics (筹码分布)**: Profit chip ratio (获利筹码比例), 70% & 90% chip concentration ranges (筹码集中度)

* **Track 9.3: 15 Built-in Technical & Fundamental Strategy Screeners**
  - [ ] **Technical Pattern Scanners**:
    - **MA Golden Cross / Death Cross**: Fast moving average breakout with volume confirmation
    - **Bull Trend Alignment**: Classic MA5 > MA10 > MA20 > MA60 multi-timeframe alignment
    - **Volume Breakout (放量突破)**: Heavy-volume surge breaking through 60-day resistance
    - **Shrink Pullback (缩量回踩)**: Low-volume pullback touching key MA20/MA50 support
    - **Box Channel Oscillation (箱体震荡)**: Range trading between validated support floor and resistance ceiling
    - **Bottom Accumulation Volume (底部放量)**: Reversal accumulation signals at multi-month lows
    - **One Yang Engulfing Three Yin (一阳吞三阴)**: Bullish engulfing candlestick reversal pattern
    - **Chan Theory (缠论)**: Fractal (分型), Pen (笔), Central Zone (中枢), and 1st/2nd/3rd Buy/Sell point identification
    - **Elliott Wave Structure (波浪理论)**: 5-wave impulse and 3-wave ABC corrective pattern recognition
  - [ ] **Fundamental & Sentiment Screeners**:
    - **Growth Quality**: High ROE ($>15\%$), operating margin expansion, low debt-to-equity ($<0.5$), and positive Free Cash Flow
    - **Dividend Aristocrat & Value**: Low P/E ($<15$), Dividend Yield ($>4\%$), sustained dividend payout history
    - **Event-Driven & Catalyst**: Earnings surprise beat, stock split announcements, share buyback programs
    - **Expectation Repricing (预期重估)**: Valuation discount vs. forward consensus growth
    - **Dragon Head / Momentum Leader (龙头战法)**: Sector leader momentum with relative strength index leadership

* **Track 9.4: Crypto, Commodities & Digital Asset Hub**
  - [ ] Read-only balance sync for major exchanges: Coinbase, Binance, and Kraken
  - [ ] Public on-chain wallet tracking for Bitcoin (BTC), Ethereum (ETH), and Solana (SOL)
  - [ ] Live spot pricing for Gold (XAU), Silver (XAG), and Platinum (XPT)

---

### Phase 10: Pre-Aggregated Reports, Macro Reviews & Multi-Channel Webhook Alerts (Q3 2027)
*Delivering the 46 pre-aggregated report catalog from Monize and automated market digests from DSA:*

* **Track 10.1: Pre-Aggregated Financial Reports & Analytics Suite**
  - [ ] **Year-over-Year (YoY) Monthly Comparison Matrix**: Side-by-side multi-year monthly category spending, income, and savings rate comparisons
  - [ ] **Weekend vs. Weekday Spending Analysis**: Discretionary spending velocity, weekend vs. weekday spending ratio, and daily averages
  - [ ] **Cash Flow Statement Engine**: Direct and indirect cash flow statements across custom calendar periods
  - [ ] **Spending Anomaly & Spike Detection**: Automated statistical outlier detection ($>2\sigma$ historical category variance)
  - [ ] **Data Quality & Hygiene Audit**: Automated reports for uncategorized transactions, fuzzy duplicate entries, and recurring price creep
  - [ ] **Bill Payment Timeliness Matrix**: Historical tracking of on-time vs. late recurring bill payments
  - [ ] **Debt Snowball & Avalanche Payoff Planner**: Interactive debt reduction simulator with milestone payoff dates

* **Track 10.2: Daily Macro Market Review Briefing (`moneta.market.review`)**
  - [ ] Automated post-market cron generating a daily macro briefing across tracked market indices (S&P 500, Nasdaq, STI, KLCI, Hang Seng, CSI 300)
  - [ ] Market breadth metrics: Advancing vs. Declining stocks, Total market turnover, Sector & industry leaderboard
  - [ ] Benchmark comparison: Portfolio alpha/beta performance against index benchmarks synthesized into an executive summary

* **Track 10.3: Multi-Channel Webhook Notification Engine**
  - [ ] Outbound HTTP Webhook dispatchers for **Telegram Bot**, **Discord Webhook**, **Slack Bot**, **Feishu / Lark Interactive Cards**, and **Enterprise WeChat**
  - [ ] Configurable alert triggers:
    - Daily Morning Portfolio Outlook & Evening Post-Market Digest
    - Low balance & impending overdraft alerts
    - Scheduled bill payment due date & credit card statement closing warnings
    - Stock target price reached, stop-loss breach, and technical strategy triggers
  - [ ] **Markdown-to-Image Infographic Generator**: Auto-renders daily market and net worth briefings into high-resolution shareable card graphics

---

### Phase 11: Autonomous AI Copilot, Stock Intelligence & Private Local LLMs (`moneta_finance_ai_advisor`) (Q4 2027)
*Combining Monize's agentic financial tools with DSA's stock intelligence and local LLM privacy:*

* **Track 11.1: Daily AI Stock Decision Cards (`moneta.security.analysis`)**
  - [ ] Automated daily analysis generating a structured stock decision dashboard:
    - **Quant Score (0–100)** and **Trend Direction** (Bullish / Range-bound / Bearish)
    - **Action Verdict**: 🟢 Buy / 🟡 Hold / 🔴 Sell with confidence weighting
    - **Execution Price Levels**: Ideal Entry Range, Strict Stop-Loss Level, Multi-stage Take-Profit Targets
    - **Risk Alerts**: Institutional outflows, high chip dispersion, overhead resistance clusters
    - **Bullish Catalysts**: Fundamental earnings surprise, industry tailwinds, technical confluence
    - **Pre-Trade Execution Checklist**: 5-step risk-reward verification before executing orders

* **Track 11.2: Real-Time Financial News & Sentiment Search**
  - [ ] Integration with multi-engine search APIs: **Tavily**, **SerpAPI**, **Bocha**, **Brave Search**, and **SearXNG**
  - [ ] Real-time sentiment classification: Bullish / Neutral / Bearish scoring of recent company news and regulatory filings
  - [ ] Social sentiment integration: Reddit, X (Twitter), and Polymarket prediction market sentiment monitoring (US equities)

* **Track 11.3: Universal Multi-LLM Provider Gateway & Local LLM Support**
  - [ ] **Ollama Local Private Model Gateway**: 100% private, self-hosted local LLMs (Llama 3, DeepSeek-R1, Mistral, Qwen) with zero external network transmission of financial records
  - [ ] **Expanded Cloud Provider Support**: Anthropic Claude, Google Gemini, OpenAI (GPT-4o), and custom OpenAI-compatible endpoints
  - [ ] **AES-256-GCM Encryption**: Secure encryption for all stored API keys with per-user credential isolation
  - [ ] **Provider Fallback Chain & Usage Analytics**: Automatic fallback to secondary models on timeout/rate limit, with token and cost tracking

* **Track 11.4: Real-Time Streaming (SSE) & Dynamic Agentic Tool-Calling Loop**
  - [ ] **Server-Sent Events (SSE) Streaming**: Token-by-token streaming chat interface for natural conversation flow
  - [ ] **6 Core Financial Agentic Tools**:
    1. `get_account_balances`: Real-time balances and credit utilization
    2. `get_transactions_by_period`: Filtered transaction ledger queries
    3. `get_spending_by_category`: Deep category and subcategory spending aggregations
    4. `get_income_summary`: Income breakdown across salary, dividends, rental, and interest
    5. `get_net_worth_history`: Multi-period historical net worth snapshots
    6. `get_period_comparison`: Period-over-period financial variance calculations
  - [ ] **90-Day Predictive Cash Flow Forecasting**: Seasonal regression forecasting for account balance trajectories
  - [ ] **SaaS Subscription Negotiation Assistant**: Automated cancellation and reduction request drafts for unused recurring charges

---

### Phase 12: Native Mobile Apps (iOS & Android) & PWA (Q4 2027)
*Delivering dedicated mobile apps and responsive fast-logging interfaces:*

- [ ] **Cross-Platform Native Apps (iOS & Android)**: High-performance mobile applications built with React Native / Flutter connecting securely to Moneta via REST/JSON-RPC and MCP APIs
- [ ] **Biometric Security**: Native Face ID, Touch ID, and Android Biometric Prompt authentication
- [ ] **Offline-First Architecture**: Local SQLite cache enabling full offline checkbook browsing with background bidirectional synchronization and conflict resolution
- [ ] **Native Camera Receipt & Invoice OCR**: In-app camera scanner capturing receipts and parsing itemized line items into transaction splits via on-device or cloud OCR
- [ ] **Real-Time Push Notifications**: Native iOS (APNs) and Android (FCM) alerts for upcoming bill due dates, low balance thresholds, credit card settlement dates, and stock price alerts
- [ ] **Home Screen Widgets & Fast Capture**: iOS Lock Screen / Home Screen Widgets and Android App Widgets for 1-tap rapid expense capture and live net worth glance
- [ ] **Mobile Progressive Web App (PWA)**: Web-based PWA fallback for instant desktop/mobile browser installation without app store download
- [ ] **Smartwatch Companions (Apple Watch & Wear OS)**: Quick glance at daily checking balance, monthly budget progress, and 1-tap voice expense logging

---

## 💡 How to Champion a Feature
If you'd like to work on any item from this roadmap:
1. Check the [Issues tab](https://github.com/lohwswilson/moneta_finance/issues) or open a new Proposal Issue.
2. Discuss the design approach with maintainers.
3. Submit a Pull Request targeting branch `18.0`.
