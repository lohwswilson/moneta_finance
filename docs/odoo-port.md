# Monize -> Odoo 18 Port (`moneta_finance`)

The Monize personal-finance application (NestJS + TypeORM + PostgreSQL) is
ported to Odoo 18 as the `moneta_finance` module. This is a
**rewrite, not a translation**: the Odoo module is faithful to Monize's
*semantics* (sign conventions, balance predicate, transfer pairing, average-cost
basis, null propagation, budget actuals, recurring frequencies, loan amortization,
Monte Carlo simulation, and emergency estate access) while adopting
Odoo's native users/auth/i18n/currencies/reports.

## Mapping: Monize concept -> Odoo model

| Monize (NestJS) | Odoo 18 (`moneta_finance`) |
|---|---|
| Postgres RLS + GUCs (`withScopedDb`, `user_id` on every table) | `ir.rule` record rules per owned model: `group_moneta_user` -> own rows, `group_moneta_manager` -> all |
| `accounts`, three-layer balance (atomic delta / recompute / cron) | `moneta.account`: stored `current_balance`/`cleared_balance` maintained by parameterized SQL (`_apply_balance_delta`, `_recompute_balance`, `_cron_roll_in_balances`) |
| `transactions` + `transaction_splits` | `moneta.transaction` + `moneta.transaction.split` (with receipt image/PDF attachments, running balances, 1-click Clr toggle, payee quickfill) |
| `categories` (`category_type`, `is_income`, `is_system`, emoji icons, inheritance) | `moneta.category`; child inherits `is_income`, color and emoji icon from parent; `is_system` protected from unlink; per-user default seeding |
| `payees` + `payee_aliases` (tiered match) | `moneta.payee` + `moneta.payee.alias`; tiered resolver (exact -> wildcard alias -> normalized), iterative glob, no regex |
| Budget 5-table model (budget / budget category / period / period category / alerts) | 4-model subset: `moneta.budget`, `moneta.budget.category`, `moneta.budget.period`, `moneta.budget.period.category`; visual `% Spent` progress bars and remaining budget amounts |
| `scheduled_transactions` (fixed Frequency enum) | `moneta.recurring.transaction` with frequency selection, due status tracking (overdue, today, 7d), 1-click post/skip, daily `_cron_auto_post` |
| `investment_transactions` (buy/sell/dividend/interest/split), holdings average cost | `moneta.investment.transaction`, `moneta.holding` derived by `_rebuild` (average cost, commission in basis, market value, unrealized gain/loss $, return %) |
| `strategies` (GEM dual-momentum) | `moneta.gem.strategy` & `moneta.gem.signal` (12-month dual-momentum lookback rebalancing engine) |
| `loan_scenarios` & `loan_rate_changes` | `moneta.loan.scenario`, `moneta.loan.amortization.line`, `moneta.loan.rate.change` (amortization tables, prepayments, interest & time saved) |
| `monte_carlo` | `moneta.monte.carlo`, `moneta.monte.carlo.path` (1,000 stochastic geometric simulations, success probability %, P10/P50/P90 trajectory) |
| `emergency_access` | `moneta.emergency.contact` (designated trusted contacts, security waiting periods, estate notes) |
| `delegation` / joint accounts | `moneta.account.share` (granular read-only, read-write, joint-owner sharing) |
| `monthly_account_balances` + net worth | `moneta.account.balance.monthly` rebuilt on write; aggregation converts to base currency at month rate with graph/pivot analysis |
| Bank statement reconciliation wizard | `moneta.reconciliation.wizard` (statement date & ending balance matching with live $0.00 difference target) |
| QIF/OFX/CSV import services | `moneta.import.wizard` (transient) |
| `institutions` | `moneta.institution` |
| Monize executive dashboard | `moneta.dashboard` (4 KPI hero cards, quick action launchpad) |

## Deferred (documented, not implemented)

- AI assistant + MCP server + AI relay (external integration)
- MNY / MSISAM binary raw decrypter (Quicken/MS Money export to standard QIF/OFX/CSV is fully supported instead)
- OAuth/OIDC provider + PAT scopes + step-up (Odoo native auth/2FA covers this)
- Custom-report CRUD builder (use Odoo native pivot/graph/spreadsheet instead)
- Full 23-locale translation (`.pot` + English shipped; translate at acceptance)
- Scheduled-transaction overrides (one-off date modifications)

## Layout

```
odoo_addons/moneta_finance/
  models/          account, account_share, transaction(+split), category, payee(+alias),
                   budget, recurring, institution, investment(+price/transaction/holding/allocation),
                   gem_strategy, net_worth, dashboard, tag, loan, monte_carlo, emergency_access, res_users
  security/        groups, ir.model.access.csv, moneta_record_rules.xml
  data/            default_categories.xml, moneta_cron.xml
  views/           per-model views + menus + dashboard + net-worth graph + gem_strategy + loan + monte_carlo + emergency
  wizards/         import wizard (QIF/OFX/CSV), reconciliation wizard
  migrations/      18.0.1.x.y pre/post scripts
  tests/           TransactionCase suite (all post_install)
```

Version history: 
- `18.0.1.0.0` Phase 0 (foundation, isolation, balances, transfers, recurring, import)
- `18.0.1.1.0` Phase 1 (institutions, categories, payees, budgets, reconciliation, dashboard)
- `18.0.1.2.0` Phase 2 (investments, average cost, realized gains)
- `18.0.1.3.0` Phase 3 (net-worth monthly snapshots, base-currency aggregation, graph)
- `18.0.1.4.0` (delete guards for accounts and categories)
- `18.0.1.5.0` (v1.14.0 parity: multi-asset weighting, payee analytics, GEM strategy, joint accounts)
- `18.0.2.0.0` (Quicken Premier & Advanced Suite: Checkbook Register running balances, 1-click Clr toggle, Bank Reconciler wizard, Visual Budget progress gauges, Modern Executive Dashboard, Loan & Mortgage Amortization engine, Monte Carlo Wealth Simulator, Receipt Attachments, Emergency Digital Estate Access).
