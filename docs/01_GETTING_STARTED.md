# Getting Started with Moneta Personal Finance

Welcome to **Moneta Personal Finance** for Odoo 18. This guide walks you through initial onboarding, base currency configuration, creating your first accounts, and importing financial data.

---

## 1. System Requirements & Prerequisites

Moneta runs natively on **Odoo 18.0 (Community or Enterprise)** with Python 3.10+.

### Required Python Libraries
To support live Yahoo Finance quote syncing and financial calculations, ensure the following Python packages are installed in your Odoo virtual environment:

```bash
pip install yfinance pandas numpy matplotlib
```

---

## 2. Installation

1. **Clone the Repository** into your Odoo custom addons directory:
   ```bash
   cd /path/to/your/custom_addons
   git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git
   ```

2. **Update Addons List & Install**:
   * Navigate to Odoo in your browser $\rightarrow$ **Apps**.
   * Click **Update Apps List**.
   * Search for `Moneta Personal Finance` and click **Activate / Install**.
   * Or run via terminal:
     ```bash
     ./odoo-bin -c odoo.conf -d <your_database> -i moneta_finance
     ```

---

## 3. Initial Configuration

### Setting Your Base Currency
Moneta automatically converts foreign accounts, international stocks (e.g. USD, EUR, GBP), and multi-currency assets into your company's primary base currency (e.g., **SGD**, **USD**, or **EUR**).

1. Go to **Accounting / Settings** $\rightarrow$ **Companies**.
2. Set your primary currency (e.g. `SGD`).
3. Ensure active exchange rates exist in **Invoicing / Settings** $\rightarrow$ **Currencies**.

---

## 4. Creating Your First Accounts

Navigate to **Moneta** $\rightarrow$ **Accounts** $\rightarrow$ **New**:

| Account Type | Visual Theme | Typical Usage | Key Configuration Fields |
| :--- | :--- | :--- | :--- |
| **Checking / Chequing** | 🟢 Emerald Green | Primary daily spending bank account | Initial Balance, Bank Name |
| **Savings** | 🟢 Emerald Green | High-yield savings, emergency fund | Interest Rate, Initial Balance |
| **Brokerage** | 🔵 Royal Blue | Stocks, ETFs, mutual funds | Cash balance, Multi-currency (USD/SGD) |
| **Credit Card** | 🟣 Royal Purple | Credit cards & revolving credit | Credit Limit, Statement Cycle Day, Payment Due Day |
| **Loan / Mortgage** | 🔴 Crimson Red | Home mortgages, auto loans | Principal Loan Amount, Interest Rate, Term (Months) |

---

## 5. Importing Bank Statements (CSV / QIF)

You can import transactions from your bank or software like Quicken / Mint / YNAB:

1. Go to **Moneta** $\rightarrow$ **Accounts** and open your target account.
2. Click **Import CSV / QIF** in the top action header.
3. Upload your `.csv` or `.qif` file.
4. Preview the transactions and click **Confirm Import**.

---

## 6. Next Guides
* 📖 [Banking & Checkbook Register Guide](02_BANKING_AND_RECONCILIATION.md)
* 📈 [Stock Portfolio & Investment Tracking](03_STOCKS_AND_INVESTMENTS.md)
* 🎯 [Budgets, Bills & Sinking Funds](04_BUDGETS_BILLS_AND_SUBSCRIPTIONS.md)
