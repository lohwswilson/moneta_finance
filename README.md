# Moneta Personal Finance for Odoo 18

A personal finance manager ported from the Moneta (NestJS/PostgreSQL) application
to run as an Odoo 18 module: accounts, transactions (splits / transfers / tags),
categories, payees, budgets, scheduled transactions, investments (average cost),
QIF / OFX / CSV import, and net-worth tracking -- with per-user isolation via
Odoo record rules.

## Features

- **Accounts** -- chequing, savings, credit card, loan, mortgage, line of
  credit, brokerage, cash, asset, other; opening balances; three-layer balance
  model (atomic delta on every transaction write, authoritative recompute, daily
  cron roll-in of future-dated transactions).
- **Transactions** -- signed amounts (expenses negative), states
  `unreconciled / cleared / reconciled / void`, split transactions, same-owner
  transfers (two linked legs, opposite signs), tags, reconciliation actions
  (mark cleared / reconcile / unreconcile).
- **Categories** -- `is_income` / `is_system`, child inherits the parent's
  type, system categories protected from deletion, per-user default seeding on
  group join.
- **Payees** -- per-owner unique names, wildcard aliases, tiered matcher
  (exact -> wildcard -> normalized; ReDoS-safe iterative glob).
- **Budgets** -- budget -> category lines -> monthly periods -> period lines;
  actual spending from transactions and split lines (refunds clamped),
  rollover on close, threshold alerts (warning / critical / over budget).
- **Scheduled transactions** -- fixed frequency enum, post / skip, daily
  auto-post cron.
- **Investments** -- buy / sell / dividend / interest / split; holdings derived
  by average cost (commission in basis); realized gains on sell; dividends post
  a cash income entry; unknown prices keep valuations unknown (never 0).
- **Net worth** -- per-account monthly balance snapshots rebuilt on write,
  aggregated in the base currency (assets abs - liabilities abs), graph over
  time.
- **Import** -- QIF / OFX / CSV with a CSV column-mapping step (auto-detect
  with override) and payee alias matching.
- **Dashboard** -- net worth, this-month income/expenses, upcoming bills.

## Installation

The module lives in `odoo_addons/moneta_finance`. Add `odoo_addons` to your
addons path, then install from the Apps menu or via the CLI:

```bash
uv run --no-project --with-requirements requirements.txt \
  ./odoo-bin -c odoo.conf -d <db> -i moneta_finance
```

## Tests

```bash
uv run --no-project --with-requirements requirements.txt \
  ./odoo-bin --no-http -c odoo.conf -d <db> -u moneta_finance \
  --test-enable --test-tags=moneta_finance --stop-after-init
```

All tests are `post_install` tagged; the module's full suite runs on upgrade
with `--test-tags=moneta_finance`.

## Demo data

Installing with demo data loads two users (the installer + `demo_user`), a full
chart of accounts, payees with aliases, transactions including a transfer, a
split and a void, budgets, scheduled transactions, securities with prices and
investment buys/sells, and net-worth snapshots.

See `docs/odoo-port.md` for the Moneta-to-Odoo mapping, deferred features and
known deviations.
