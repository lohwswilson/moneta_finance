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

## 4. Investment Transactions (Trades & Dividends)

Moneta records four primary trade types:
1. **Buy**: Increases quantity and adjusts total cost basis.
2. **Sell**: Decreases quantity and locks realized capital gains.
3. **Dividend (Cash)**: Credits the linked brokerage cash balance.
4. **Reinvest Dividend (DRIP)**: Adds shares at the reinvestment price without cash withdrawal.
