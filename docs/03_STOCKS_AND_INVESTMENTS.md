# Stock Portfolio & Investment Tracking

Moneta includes a comprehensive investment center featuring live quote fetching, multi-lot holdings, average cost basis accounting, dividend logging, and multi-currency valuation.

---

## 1. Live Yahoo Finance Quote Synchronization

Moneta seamlessly syncs market quotes directly from Yahoo Finance:

* **Automatic Hourly Background Sync**: An automated Odoo Cron job (`cron_moneta_fetch_security_quotes`) updates price history every hour during market sessions.
* **1-Click Manual Refresh**: Click **🔄 Refresh All Live Quotes** from any Holding list or form view to fetch live quotes for all portfolio tickers simultaneously.

---

## 2. Security Master & Multi-Currency Handling

Each security record (`moneta.security`) holds:
* **Ticker Symbol**: e.g., `AAPL`, `MSFT`, `NVDA`, `D05.SI`, `CSPX.L`.
* **Asset Class**: Stocks, ETFs, Mutual Funds, Crypto, Bonds.
* **Trading Currency**: e.g. `USD`, `SGD`, `EUR`.

> **Multi-Currency FX Valuation**: If a stock trades in `USD` and your base company currency is `SGD`, Moneta automatically converts the holding's market value, cost basis, and unrealized gains into `SGD` in real time.

---

## 3. Average Cost Basis & Gain/Loss Formulas

Moneta utilizes the industry-standard **Average Cost Basis** method:

$$\text{Average Unit Cost} = \frac{\sum \text{Total Buy Cost} - \sum \text{Cost of Sold Shares}}{\text{Remaining Quantity}}$$

$$\text{Market Value} = \text{Quantity} \times \text{Latest Close Price}$$

$$\text{Unrealized Gain / Loss} = \text{Market Value} - \text{Total Cost Basis}$$

$$\text{Gain \%} = \left( \frac{\text{Market Value} - \text{Total Cost Basis}}{\text{Total Cost Basis}} \right) \times 100$$

---

## 4. Investment Transactions (Trades & Corporate Actions)

Moneta records five primary transaction types:
1. **Buy**: Increases quantity and adjusts total cost basis with broker commission included.
2. **Sell**: Decreases quantity and records realized capital gains against the running average cost.
3. **Dividend (Cash)**: Credits the linked brokerage cash balance and records investment income.
4. **Interest**: Logs fixed-income interest payments into the cash register.
5. **Split (Corporate Action)**: Adjusts share quantities by the split ratio (e.g. 2:1, 3:1, 10:1) and proportionally scales down average unit cost with zero basis distortion.

---

## 5. Trade Statement Reconciliation & `Clr` Status

Just like cash registers, investment transactions support full reconciliation tracking:
* **Status Flags**: `Unreconciled` (⚪), `Cleared` (🔵 Clr), `Reconciled` (🟢 R), and `Void` (🚫 Void).
* **1-Click `Clr` Toggle**: Click the `Clr` button on any trade row to cycle status as you verify monthly brokerage trade confirmations.
* **Void Isolation**: Voiding a trade immediately excludes it from portfolio quantity, cost basis, TWR/MWR calculations, and net worth history without deleting the audit trail.
