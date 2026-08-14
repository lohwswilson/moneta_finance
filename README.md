# Moneta Personal Finance for Odoo 18

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-purple.svg)](https://www.odoo.com)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)

**Moneta Personal Finance** is a full-featured, open-source personal wealth, budgeting, and portfolio management module built natively for **Odoo 18** (inspired by classic desktop personal finance tools like *Microsoft Money* and *Quicken*).

It provides complete multi-account tracking, split transactions, category budgets, scheduled bills, stock portfolio management with average-cost accounting, dual-momentum strategies (GEM), QIF/OFX/CSV bank statement imports, and automated net-worth reporting with strict per-user data isolation.

---

## Features

- **Accounts & Registers** — Chequing, savings, credit cards, loans, mortgages, lines of credit, brokerages, and cash with atomic delta balance calculations and reconciled states.
- **Transactions & Splits** — Signed amounts, categorized split lines, same-owner transfers (two linked legs), tags, and reconciliation workflows (*unreconciled / cleared / reconciled*).
- **Category Budgets** — Period-based budgets (monthly/custom) with actual spend tracking, rollover on period close, and visual threshold alerts (*warning / critical / over budget*).
- **Scheduled & Recurring Bills** — Automated recurring transactions with customizable frequency schedules and daily auto-post background crons.
- **Investments & Portfolio** — Multi-asset tracking, daily stock prices, dividend/interest reinvestment, average cost basis, realized capital gains, and Global Equities Momentum (GEM) strategy allocation signals.
- **Net Worth Tracking** — Per-account historical monthly balance snapshots aggregated in your base currency with interactive charts.
- **Statement Imports** — QIF, OFX/QFX, and CSV statement import wizard with auto-detection column mapping and wildcard payee alias matching.
- **Multi-User & Joint Accounts** — Granular per-user data isolation via Odoo record rules (`group_moneta_user`), with shared joint account permissions.

---

## Prerequisites

Before installing this module, ensure you have:
1. **Odoo 18.0** (Community or Enterprise edition)
2. **PostgreSQL** (version 14 or higher)
3. **Python 3.10+** (managed via `uv` or `pip`)

---

## Getting Started

### 1. Clone the Module
Clone this repository into your custom Odoo addons directory:

```bash
cd /path/to/your/custom_addons
git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git
```

---

### 2. Setting Up Odoo 18 (If Starting from Scratch)

If you do not have an active Odoo 18 environment yet, set one up using [`uv`](https://github.com/astral-sh/uv):

```bash
# 1. Clone Odoo 18 source
git clone -b 18.0 --depth 1 https://github.com/odoo/odoo.git odoo18
cd odoo18

# 2. Create virtual environment & install requirements
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt

# 3. Create your odoo.conf configuration file
cat << 'CONF' > odoo.conf
[options]
admin_passwd = admin_master_password
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
addons_path = /path/to/odoo18/addons,/path/to/your/custom_addons
http_port = 8069
CONF
```

> **Tip:** Ensure your PostgreSQL server is running and the database user has sufficient privileges (`createuser -s odoo`).

---

### 3. Install & Run Moneta in Odoo

#### A. Starting Odoo and Installing via CLI:
```bash
# Start Odoo and initialize the moneta_finance module on database <your_db_name>
./odoo-bin -c odoo.conf -d my_finance_db -i moneta_finance
```

#### B. Installing via the Odoo Web Interface:
1. Start Odoo: `./odoo-bin -c odoo.conf`
2. Open your browser and navigate to `http://localhost:8069`
3. Log in as Administrator and activate **Developer Mode** (*Settings -> General Settings -> Activate the developer mode*).
4. Navigate to **Apps** -> Click **Update Apps List**.
5. Search for `Moneta Personal Finance` and click **Activate**.

---

### 4. User Access & Permissions

Moneta enforces strict per-user record isolation:
1. Go to **Settings -> Users & Companies -> Users**.
2. Select a user and scroll down to the **Moneta Finance** access group:
   - **User**: Can view and manage their own private accounts, transactions, budgets, and investments.
   - **Manager**: Full administrative access across all accounts and module configuration.

---

## Running the Test Suite

Run the automated test suite using `odoo-bin`:

```bash
./odoo-bin -c odoo.conf -d my_finance_db -u moneta_finance \
  --test-enable --test-tags=moneta_finance --stop-after-init
```

---

## Demo Data

To load pre-configured demo data (sample chart of accounts, payees, split transactions, investment holdings, and budgets) for testing, initialize with the `--without-demo=False` flag or install on a database created with demo data enabled:

```bash
./odoo-bin -c odoo.conf -d test_moneta_db -i moneta_finance --without-demo=False
```

---

## License

This project is licensed under the [GNU Lesser General Public License v3.0 (LGPL-3)](LICENSE).
