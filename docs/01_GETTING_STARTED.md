# Getting Started with Moneta Personal Finance

Welcome to **Moneta Personal Finance**. This guide walks you through setting up Moneta using either the **30-second Docker container quickstart** or **manual installation into an existing environment**, followed by base currency configuration and setting up your first accounts.

---

## ⚡ Method 1: 30-Second Docker Quickstart (Recommended)

The repository includes a ready-to-use [`docker-compose.yml`](https://github.com/lohwswilson/moneta_finance/blob/18.0/docker-compose.yml) that automatically provisions all Moneta modules with persistent storage.

### 1. Launch Containers
```bash
# Clone the repository
git clone https://github.com/lohwswilson/moneta_finance.git
cd moneta_finance

# Start Moneta Personal Finance in the background
docker compose up -d
```

### 2. Access Moneta
* Open your browser at **`http://localhost:8069`**
* **Database**: `moneta_dev` (auto-created)
* **Default Login**: `admin` / `admin`
* All Moneta modules (`moneta_finance`, `moneta_finance_property`, `moneta_finance_singapore`, `moneta_finance_malaysia`, `moneta_finance_ai_advisor`) are automatically initialized.

### 3. Common Docker Commands
```bash
# View live logs
docker compose logs -f web

# Restart services
docker compose restart

# Stop services
docker compose down
```

---

## 🛠️ Method 2: Manual Installation (Existing Environment)

For users who prefer installing Moneta into an existing self-hosted environment:

### 1. Install Required Python Dependencies
To support live Yahoo Finance quote syncing and financial computations:

```bash
pip install yfinance pandas numpy matplotlib
```

### 2. Clone Moneta into Your Addons Directory
```bash
git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git /path/to/your/custom_addons/moneta_finance
```

### 3. Activate the Modules
* **Via Web Interface**:
  1. Open your browser and navigate to **Apps**.
  2. Click **Update Apps List**.
  3. Search for `Moneta Personal Finance` and click **Activate / Install**.
* **Via Command Line**:
  ```bash
  odoo-bin -c odoo.conf -d <your_database> -i moneta_finance,moneta_finance_property,moneta_finance_singapore,moneta_finance_malaysia
  ```

---

## ⚙️ Initial Configuration

### Setting Your Base Currency
Moneta automatically converts foreign accounts, international stocks (e.g., USD, EUR, GBP), and multi-currency assets into your primary base currency (e.g., **SGD**, **USD**, or **EUR**).

1. Go to **Settings** $\rightarrow$ **Companies**.
2. Set your primary currency (e.g. `SGD` or `USD`).
3. Ensure active exchange rates exist in **Settings** $\rightarrow$ **Currencies**.

---

## 🎴 Creating Your First Accounts

Navigate to **Moneta** $\rightarrow$ **Accounts** $\rightarrow$ **New**:

| Account Type | Visual Theme | Typical Usage | Key Configuration Fields |
| :--- | :--- | :--- | :--- |
| **Checking** | 🟢 Emerald Green | Primary daily spending bank account | Initial Balance, Bank Name |
| **Savings** | 🟢 Emerald Green | High-yield savings, emergency fund | Interest Rate (APY), Initial Balance |
| **Brokerage** | 🔵 Royal Blue | Stocks, ETFs, mutual funds | Cash balance, Multi-currency (USD/SGD) |
| **Credit Card** | 🟣 Royal Purple | Credit cards & revolving credit | Credit Limit, Statement Cycle Day, Payment Due Day |
| **Loan / Mortgage** | 🔴 Crimson Red | Home mortgages, auto loans | Principal Loan Amount, Interest Rate, Term (Months) |
| **Singapore CPF/SRS** | 🐬 Teal Accent | Singapore Central Provident Fund | Account selection (`OA`, `SA`, `MA`, `RA`, `SRS`) |
| **Malaysia EPF** | 🟡 Gold Accent | Malaysia KWSP Retirement | Account selection (`Akaun 1`, `Akaun 2`, `Akaun 3`) |
