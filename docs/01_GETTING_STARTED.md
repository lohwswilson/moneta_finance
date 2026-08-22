# Getting Started with Moneta Personal Finance

Welcome to **Moneta Personal Finance** for Odoo 18. This guide walks you through the 30-second Docker container quickstart, manual native installation, base currency configuration, and setting up your first accounts.

---

## ⚡ Method 1: 30-Second Docker Quickstart (Recommended)

The repository includes a ready-to-use [`docker-compose.yml`](https://github.com/lohwswilson/moneta_finance/blob/18.0/docker-compose.yml) that automatically provisions **PostgreSQL 16** and **Odoo 18.0** with all Moneta modules pre-installed.

### 1. Launch Containers
```bash
# Clone the repository
git clone https://github.com/lohwswilson/moneta_finance.git
cd moneta_finance

# Start PostgreSQL and Odoo 18 in background
docker compose up -d
```

### 2. Access Odoo
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

## 🛠️ Method 2: Manual Native Odoo 18 Installation

If you already run a local or production Odoo 18 instance:

### 1. Install Required Python Packages
```bash
pip install yfinance pandas numpy matplotlib
```

### 2. Add to Addons Path
Clone the repository into your Odoo custom addons directory:
```bash
cd /path/to/your/custom_addons
git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git
```

### 3. Install in Odoo
* Navigate to Odoo in your browser $\rightarrow$ **Apps**.
* Click **Update Apps List**.
* Search for `Moneta Personal Finance` and click **Activate / Install**.
* Or install via terminal command line:
  ```bash
  ./odoo-bin -c odoo.conf -d <your_database> -i moneta_finance,moneta_finance_property,moneta_finance_singapore,moneta_finance_malaysia
  ```

---

## ⚙️ Initial Configuration

### Setting Your Base Currency
Moneta automatically converts foreign accounts, international stocks (e.g., USD, EUR, GBP), and multi-currency assets into your company's primary base currency (e.g., **SGD**, **USD**, or **EUR**).

1. Go to **Accounting / Settings** $\rightarrow$ **Companies**.
2. Set your primary currency (e.g. `SGD` or `USD`).
3. Ensure active exchange rates exist in **Invoicing / Settings** $\rightarrow$ **Currencies**.

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
