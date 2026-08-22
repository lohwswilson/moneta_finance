# Local Development Environment & Setup Guide

This guide walks you through preparing a local development environment for contributing to, customizing, and debugging **Moneta Personal Finance**.

---

## 🛠️ 1. Prerequisites & Tooling

Before setting up Moneta, ensure your development machine has the following tools installed:

| Requirement | Recommended Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.10`, `3.11`, or `3.12` | Runtime engine |
| **PostgreSQL** | `15` or `16` | Database server |
| **Git** | `2.40+` | Version control |
| **Docker & Docker Compose** | *(Optional)* | Containerized isolated development |
| **VS Code / PyCharm / Cursor** | Latest | Recommended IDEs |

---

## 🐍 2. Setting Up Python Virtual Environment

It is recommended to isolate dependencies inside a dedicated Python virtual environment:

```bash
# 1. Create a virtual environment
python3 -m venv ~/.venvs/moneta-dev

# 2. Activate the virtual environment
# On macOS / Linux:
source ~/.venvs/moneta-dev/bin/activate
# On Windows (PowerShell):
# ~/.venvs/moneta-dev/Scripts/Activate.ps1

# 3. Install core scientific and financial dependencies
pip install --upgrade pip
pip install yfinance pandas numpy matplotlib psycopg2-binary
```

---

## 🐘 3. PostgreSQL Database Setup

Create a dedicated local PostgreSQL role and development database:

```bash
# Create the PostgreSQL user (if not already existing)
createuser -s -d -r odoo

# Set the password for the odoo user (e.g. 'odoo')
psql -d postgres -c "ALTER USER odoo WITH PASSWORD 'odoo';"

# Create a clean development database
createdb -O odoo moneta_dev
```

---

## ⚙️ 4. Development Configuration (`odoo.conf`)

Create a development configuration file `odoo-dev.conf` in your local development folder:

```ini
[options]
; Paths to core addons and the moneta_finance repository
addons_path = /path/to/odoo/addons,/path/to/moneta_finance

; Database connection
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
db_name = moneta_dev

; Developer productivity flags
dev_mode = all
limit_time_cpu = 1200
limit_time_real = 2400
log_level = info
```

---

## 🚀 5. Running Moneta in Developer Mode

Launch the development server with **live reload flags enabled**:

```bash
# Start Odoo with live reload and update Moneta modules
./odoo-bin -c odoo-dev.conf -d moneta_dev -u moneta_finance,moneta_finance_property,moneta_finance_singapore,moneta_finance_malaysia --dev=all
```

### 💡 What `--dev=all` Enables:
* **`--dev=reload`**: Automatically restarts the server when Python source files are modified.
* **`--dev=xml`**: Instantly reloads QWeb templates, XML form views, and tree views on browser refresh without restarting Python.
* **`--dev=wdb` / `--dev=pdb`**: Automatically launches an interactive debugger when an unhandled exception occurs.

---

## 🧪 6. Running Automated Test Suites

Moneta includes full test suites covering the three-layer balance engine, transfer reconciliation, and investment math:

```bash
# Run all unit tests for moneta_finance on a temporary database
./odoo-bin -c odoo-dev.conf -d moneta_test --test-enable --stop-after-init -i moneta_finance --log-level=test
```

### Running Specific Test Classes:
```bash
# Run only banking and transfer reconciliation tests
./odoo-bin -c odoo-dev.conf -d moneta_test --test-enable --stop-after-init --test-tags=moneta_finance.test_reconciliation
```

---

## 💻 7. Recommended VS Code / Cursor Configuration

Create `.vscode/launch.json` in your workspace for one-click breakpoint debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Moneta Personal Finance",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/odoo-bin",
      "args": [
        "-c", "${workspaceFolder}/odoo-dev.conf",
        "-d", "moneta_dev",
        "-u", "moneta_finance",
        "--dev=all"
      ],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

---

## 📐 8. Code & Architectural Conventions

When developing new features for Moneta:

1. **Precision Currency Math**: Always use `digits=(20, 4)` and `round(amount, 4)` to preserve decimal precision across international currencies.
2. **Atomic Balance Updates**: Use `_apply_balance_delta(account_id, current_delta, cleared_delta)` for balance changes to guarantee transactional ACID compliance.
3. **Multi-User Isolation**: Ensure all domain queries filter by `('user_id', '=', self.env.user.id)` or respect joint sharing grants via `share_ids`.
4. **Documentation**: When adding new models or features, update the relevant documentation in `docs/` and run `zensical build` to verify formatting.
