# Monize -> Odoo 18 Port (`moneta_finance`)

The Monize personal-finance application (NestJS + TypeORM + PostgreSQL) is
ported to Odoo 18 as the `moneta_finance` module in `odoo_addons/`. This is a
**rewrite, not a translation**: the Odoo module is faithful to Monize's
*semantics* (sign conventions, balance predicate, transfer pairing, average-cost
basis, null propagation, budget actuals, recurring frequencies) while adopting
Odoo's native users/auth/i18n/currencies/reports.

## Mapping: Monize concept -> Odoo model

| Monize (NestJS) | Odoo 18 (`moneta_finance`) |
|---|---|
| Postgres RLS + GUCs (`withScopedDb`, `user_id` on every table) | `ir.rule` record rules per owned model: `group_moneta_user` -> own rows, `group_moneta_manager` -> all |
| `accounts`, three-layer balance (atomic delta / recompute / cron) | `moneta.account`: stored `current_balance`/`cleared_balance` maintained by parameterized SQL (`_apply_balance_delta`, `_recompute_balance`, `_cron_roll_in_balances`) |
| `transactions` + `transaction_splits` | `moneta.transaction` + `moneta.transaction.split` (split children live in a separate model and are never summed into balances) |
| `categories` (`is_income`, `is_system`, parent inheritance) | `moneta.category`; child inherits `is_income` from parent; `is_system` protected from unlink; per-user default seeding on `res.users` group join |
| `payees` + `payee_aliases` (tiered match) | `moneta.payee` + `moneta.payee.alias`; tiered resolver (exact -> wildcard alias -> normalized), iterative glob, no regex |
| Budget 5-table model (budget / budget category / period / period category / alerts) | 4-model subset: `moneta.budget`, `moneta.budget.category`, `moneta.budget.period`, `moneta.budget.period.category`; alerts computed (warn / critical / over budget) |
| `scheduled_transactions` (fixed Frequency enum) | `moneta.recurring.transaction` with the same frequency selection, `post()`/`skip()`, daily `_cron_auto_post` |
| `investment_transactions` (buy/sell/dividend/interest/split), holdings average cost | `moneta.investment.transaction`, holdings derived by `_rebuild` (average cost, commission in basis, realized gains on sell) |
| `monthly_account_balances` + net worth | `moneta.account.balance.monthly` rebuilt on write; aggregation converts to the base currency at the month's rate |
| QIF/OFX/CSV import services | `moneta.import.wizard` (transient) |
| `institutions` | `moneta.institution` |
| Monize dashboard tiles | `moneta.dashboard` (transient, computed tiles) |

## Deferred (documented, not implemented)

- AI assistant + MCP server + AI relay
- Monte-carlo simulations, GEM strategies, loan scenarios / amortization
- Delegation / shared access + cross-owner transfers (needs delegation)
- Emergency access, encrypted backup/restore
- MNY / MSISAM binary import, investment file import, staged import jobs
- OAuth/OIDC provider + PAT scopes + step-up (Odoo auth/2FA covers the MVP)
- Custom-report CRUD builder (use Odoo pivot/graph instead)
- Full 23-locale translation (`.pot` + English shipped; translate at acceptance)
- Investment settlement-currency FX (MVP is single-currency)
- Cross-currency transfers with FX fee (`fx_fee_percent` stored, not consumed)
- Scheduled-transaction overrides + transfer/investment schedules
- Budget velocity/health-score/seasonal/generator/annual pay-period
- Brokerage cash-sleeve sub-type, buy/sell cash impact on the brokerage balance
  (dividends/interest do post a cash entry)

### Within-scope behavioral gaps (entities ported, behaviors not yet)

These sit inside the MVP entity scope but are not yet ported; tracked here so
they are not silently absent. The two data-loss guards were added in
`18.0.1.4.0`: `moneta.account.unlink` refuses when transactions / investment
transactions exist, and `moneta.category.unlink` refuses when subcategories /
transactions / split lines / scheduled transactions reference it (regression
tests in `tests/test_delete_guards.py`).

- **Account**: reopen action; favourite sort order / reorder; daily balance
  series (`getDailyBalances`); credit-card statement-cycle computation
  (window / balance / due date / interest paid); balance forecast; account
  export (CSV / QIF).
- **Transaction**: `referenceNumber` field; bulk update / bulk delete by filter;
  aggregation endpoints (recurring-charge detection, KEY:VALUE tag breakdown,
  FX-fee summary, grouped totals, recent quick-fill).
- **Category**: reassign-transactions action; country-aware default-category
  additions.
- **Payee**: auto-merge (fuzzy clustering), category suggestions (majority from
  history), bulk deactivation, merge payees, revival match, autocomplete /
  most-used / recently-used.
- **Tag**: `icon`, `security_tags`, KEY:VALUE filtering, transaction-count
  endpoints.
- **Institution**: logo fetch / cache / refresh, account assignment action.
- **Attachments**: no transaction-attachment model (upload / download /
  MIME-whitelist / nosniff) -- Odoo `ir.attachment` is not yet wired to
  transactions.
- **Action history**: no undo / redo model across ledger mutations.

## Known deviations

- **Odoo numeric coercion kills ORM-level null propagation.** Odoo reads NULL
  numerics as `0.0` and coerces `False` assignments through `float(x or 0.0)`,
  so a Monetary field cannot carry "unknown". Unknown valuations are carried by
  explicit known-flags instead: `moneta.holding.price_known` /
  `basis_known`; the underlying columns still store NULL (verified: writing
  `False` maps to NULL; reading it back yields `0.0`).
- **Upgrade hooks**: Odoo 18 runs `pre_init_hook`/`post_init_hook` only on fresh
  installs; upgrades use versioned `migrations/<version>/` scripts. Category
  `category_type -> is_income` and holding `cost_basis -> average_cost`
  conversions live in migrations `18.0.1.1.0` / `18.0.1.2.0`.
- **Trigger machinery**: stored-compute `@api.depends` chains through
  `M2O -> O2M -> leaf` register no triggers in Odoo 18 (verified
  `TRIGGERS: []`), so cross-model derived values are refreshed explicitly
  (`flush_all()` + `env.add_to_compute` for budget actuals; non-stored computes
  for valuations; rebuild-on-write for net-worth snapshots).
- **Balance snapshots** are rebuilt on every relevant write (no debounce) --
  fine for personal-finance volumes.
- **FX precision**: native `res.currency.rate` (~6dp) vs Monize's
  `numeric(20,10)`; a custom 10dp rate model is a noted follow-up.
- **Recurring cron** is daily (Monize hourly) -- same result, simpler cadence.
- **Net-worth conversion** uses the rate at the month start (Odoo's dated-rate
  model); a missing rate leaves the contribution as 0 (documented MVP choice).
- **Demo data** loads for the installer + `demo_user`; per-user category
  seeding means the demo user's transactions carry no category refs.

## Layout

```
odoo_addons/moneta_finance/
  models/          account, account_share, transaction(+split), category, payee(+alias),
                   budget, recurring, institution, investment(+price/transaction/holding/allocation),
                   gem_strategy, net_worth, dashboard, tag, res_users (seeding hook)
  security/        groups, ir.model.access.csv, moneta_record_rules.xml
  data/            default_categories.xml, moneta_cron.xml
  views/           per-model views + menus + dashboard + net-worth graph + gem_strategy
  wizards/         import wizard (QIF/OFX/CSV + CSV column mapping)
  migrations/      18.0.1.x.y pre/post scripts
  tests/           TransactionCase suite (all post_install)
```

Version history: `18.0.1.0.0` Phase 0 (foundation, isolation, balances,
transfers, recurring, import) · `18.0.1.1.0` Phase 1 (institutions, categories
`is_income`/`is_system` + per-user seeding, payees hardening, 4-model budgets,
reconciliation, dashboard) · `18.0.1.2.0` Phase 2 (investments, average cost,
realized gains, null-propagation flags) · `18.0.1.3.0` Phase 3 (net-worth
monthly snapshots, base-currency aggregation, graph) · `18.0.1.4.0` (delete
guards: `moneta.account` / `moneta.category` refuse `unlink` before any
cascade, with `tests/test_delete_guards.py`) · `18.0.1.5.0` (v1.14.0 parity:
`moneta.security.allocation` multi-asset weighting, payee spend analytics &
recurring cadence detection, `moneta.gem.strategy` dual-momentum engine,
`moneta.account.share` joint account record rules & sharing, and multi-currency
scheduled transactions).
