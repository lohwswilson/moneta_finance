# Stock Portfolio & Investment Tracking Guide

Moneta includes a comprehensive investment center featuring live quote fetching, multi-lot holdings, average cost basis accounting, trade reconciliation, and seamless multi-currency valuation.

---

## 1. The Composite Brokerage Account Model (Cash vs. Holdings)

In Moneta, an Investment or Brokerage Account (`moneta.account`) is a **composite multi-asset account** comprising two distinct layers:

$$\text{Total Brokerage Value} = \underbrace{\text{Uninvested Cash Balance}}_{\text{Cash Register Tab}} \;+\; \underbrace{\sum_{i} \left( \text{Shares}_i \times \text{Live Price}_i \right)}_{\text{Stock & ETF Holdings Tab}}$$

```
                      ┌──────────────────────────────────────────────┐
                      │          BROKERAGE ACCOUNT ($35,450)         │
                      └──────────────────────┬───────────────────────┘
                                             │
                   ┌─────────────────────────┴─────────────────────────┐
                   ▼                                                   ▼
┌──────────────────────────────────────┐            ┌──────────────────────────────────────┐
│      1. UNINVESTED CASH PORTION      │            │     2. STOCK & ETF HOLDING PORTION   │
│         Current Cash: $5,450         │            │     Total Market Value: $30,000      │
├──────────────────────────────────────┤            ├──────────────────────────────────────┤
│ • Funds deposited from Checking      │            │ • 100 shares AAPL @ $220  = $22,000  │
│ • Cash proceeds from selling stocks  │            │ •  50 shares CSPX @ $160  =  $8,000  │
│ • Cash dividends credited from stocks│            │ • Multi-lot cost basis & FIFO/LIFO   │
│ • Interest earned on cash sweeps     │            │ • Live hourly quotes via Yahoo API   │
└──────────────────────────────────────┘            └──────────────────────────────────────┘
```

---

## 2. The 5 Core Investment Operations & Their Mechanics

### A. Funding the Brokerage Account (Cash Inflow)
* **Action**: Transfer money from **Checking** $\rightarrow$ **Brokerage**.
* **Cash Impact**: Increases the Brokerage **Cash Balance** by `+$10,000`. Stock holdings remain untouched.

### B. Buying Stocks or ETFs (`Buy`)
* **Action**: Buy 50 shares of `CSPX.L` at `$160.00/share` (Commission: `$5.00`).
* **Cash Impact**: Deducts `-$8,005.00` from your Brokerage cash balance.
* **Holdings Impact**: Adds `50 shares` to your `CSPX.L` holding record with a total cost basis of `$8,005.00` ($160.10/share).

### C. Selling Stocks or ETFs (`Sell`)
* **Action**: Sell 20 shares of `CSPX.L` at `$180.00/share` (Commission: `$5.00`).
* **Holdings Impact**:
  * Reduces `CSPX.L` quantity from `50` to `30 shares`.
  * Computes **Realized Capital Gain** (using FIFO, LIFO, HIFO, or Specific ID):
    $$\text{Net Proceeds} = (20 \times \$180) - \$5 = \$3,595$$
    $$\text{Cost Basis Disposed} = 20 \times \$160.10 = \$3,202$$
    $$\text{Realized Capital Gain} = \$3,595 - \$3,202 = \mathbf{+\$393.00}$$
* **Cash Impact**: Automatically credits `+$3,595.00` into your Brokerage **Cash Balance**.

### D. Receiving Cash Dividends (`Dividend`)
* **Action**: Apple pays a quarterly dividend of `$0.25/share` on 100 shares (`$25.00`).
* **Holdings Impact**: Share count remains 100 shares.
* **Cash Impact**: Automatically credits `+$25.00` into your Brokerage cash balance and records investment dividend income.

### E. Corporate Stock Splits (`Split`)
* **Action**: Apple executes a **4-for-1 Stock Split**.
* **Holdings Impact**: Share count multiplies by 4 (`100` $\rightarrow$ `400 shares`), while average unit cost is divided by 4 ($220 $\rightarrow$ $55).
* **Cash Impact**: **$0.00** (Zero cash impact; portfolio market value and total cost basis remain perfectly preserved).

---

## 3. Live Yahoo Finance Quote Synchronization

Moneta syncs live market quotes directly from Yahoo Finance:

* **Automatic Hourly Background Sync**: An automated background cron job (`cron_moneta_fetch_security_quotes`) updates price history every hour during market sessions.
* **1-Click Manual Refresh**: Click **🔄 Refresh All Live Quotes** from any Holding list or form view to fetch live quotes for all portfolio tickers simultaneously.

---

## 4. Multi-Currency FX Valuation

If you invest in foreign stock markets (e.g. US stocks in `USD`, London UCITS ETFs in `USD`/`GBP`, or Singapore SGX stocks in `SGD`):

* **Native Currency Accounting**: Each stock holding tracks quantity, cost basis, and latest market price in its native trading currency.
* **Real-Time FX Conversion**: When computing total account value and Net Worth, Moneta converts each individual holding's market value, cost basis, and unrealized gains into your base currency using the real-time exchange rate table.

---

## 5. Cost Basis & Gain/Loss Formulas

Moneta supports both **Average Cost Basis** and **Tax-Lot Accounting (FIFO, LIFO, HIFO, Specific Identification)**:

$$\text{Average Unit Cost} = \frac{\sum \text{Total Buy Cost} - \sum \text{Cost of Sold Shares}}{\text{Remaining Quantity}}$$

$$\text{Market Value} = \text{Quantity} \times \text{Latest Close Price}$$

$$\text{Unrealized Gain / Loss} = \text{Market Value} - \text{Total Cost Basis}$$

$$\text{Gain \%} = \left( \frac{\text{Market Value} - \text{Total Cost Basis}}{\text{Total Cost Basis}} \right) \times 100$$

---

## 6. Trade Statement Reconciliation & `Clr` Status

Just like bank checkbook registers, investment transactions support full reconciliation tracking:

* **Status Flags**: `Unreconciled` (⚪), `Cleared` (🔵 Clr), `Reconciled` (🟢 R), and `Void` (🚫 Void).
* **1-Click `Clr` Toggle**: Click the `Clr` button on any trade row to cycle status as you verify monthly brokerage trade confirmations.
* **Void Isolation**: Voiding a trade immediately excludes it from portfolio quantity, cost basis, TWR/MWR calculations, and net worth history without deleting the audit trail.
