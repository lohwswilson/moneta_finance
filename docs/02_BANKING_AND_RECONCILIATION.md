# Banking, Checkbook Registers & Statement Reconciliation

Moneta incorporates the battle-tested checkbook register architecture of **Quicken Premier** with real-time running balance recalculation, multi-currency transfer handling, and interactive bank statement reconciliation.

---

## 1. Color-Coded Account Dashboard

Accounts are visually categorized with color accents and metrics:

* 🟢 **Emerald Green Cards (Cash & Bank Accounts)**: Shows available cash, cleared balance, and quick reconcile links.
* 🔵 **Royal Blue Cards (Brokerage & Stock Accounts)**: Shows live stock market value, uninvested cash, and total return %.
* 🟣 **Royal Purple Cards (Credit Cards)**: Shows current card balance, credit limit, statement closing day, and payment due date.
* 🔴 **Crimson Red Cards (Loans & Mortgages)**: Shows outstanding principal debt, monthly P&I payment, and estimated payoff date.

---

## 2. Checkbook Register & Running Balances

When opening any account, the **Register & Transactions** tab displays an interactive checkbook ledger:

* **Chronological Ordering & Tiebreakers**: Sorted chronologically with credit-before-debit tiebreaking (`transaction_date desc, amount asc, id desc`). On identical dates and import timestamps, deposits/credits are listed before debits/payments so running balances never dip negative on same-day funded purchases.
* **Running Balance Calculation**: Automatically computes the exact point-in-time account balance across all historical rows using high-performance SQL window partitions.
* **1-Click `Clr` Toggle**:
  Clicking the `Clr` button on any row toggles its reconciliation status:
  $$\text{Unreconciled (Empty)} \longrightarrow \text{Cleared (🔵 Clr)} \longrightarrow \text{Reconciled (🟢 R)}$$

---

## 3. Account Transfers & Cross-Currency Transfers

Moneta uses a **two-legged linked transfer engine** to handle money movement between accounts.

```
Source Account (SGD Bank)                            Destination Account (USD Brokerage)
┌──────────────────────────────────────┐             ┌──────────────────────────────────────┐
│ Currency: SGD                        │    Linked   │ Currency: USD                        │
│ Date: 2026-08-22                     │  Transfer   │ Date: 2026-08-22                     │
│ Payee: Transfer : IBKR USD Cash      │ ──────────► │ Payee: Transfer : DBS SGD Checking   │
│ Amount: -SGD $1,350.00 (Outflow)     │             │ Amount: +USD $1,000.00 (Inflow)      │
│ (Rate: 1 USD = 1.35 SGD)             │             │ (Native USD ledger balance updated)  │
└──────────────────────────────────────┘             └──────────────────────────────────────┘
```

### A. Same-Currency Transfers
* **Automatic Counterpart Leg**: Creating a transfer in Checking (`-$500`) automatically generates the mirrored counterpart leg in Savings (`+$500`) with `linked_transaction_id` mutually linking both rows.
* **Pass-Through Budget Protection**: Transfers are excluded from Income and Expense reporting to prevent internal money movements from distorting your spending budget.

### B. Cross-Currency Transfers (Different Currencies)
Moneta natively supports transfers between accounts denominated in different currencies (e.g. `SGD` $\rightarrow$ `USD`, or `USD` $\rightarrow$ `EUR`, `MYR`, `GBP`, `JPY`):

1. **Automatic Exchange Rate Conversion**: When you create the transfer in the source currency (e.g. `-$1,350.00 SGD`), Moneta uses Odoo's live exchange rate table (`res.currency`) on the transaction date to calculate and post the target amount in the destination account's native currency (e.g. `+$1,000.00 USD`).
2. **Realized Bank Spread & Fee Overrides**: If your bank or remittance service (e.g. Wise, DBS Remit, Revolut) charged a wire fee or applied a custom FX spread, you can edit the exact received amount on the destination leg (e.g. change `$1,000.00` to `$996.50 USD`). Moneta preserves each account's independent local currency amount while maintaining the linked transfer pair.
3. **Smart Match Across Imported Foreign Statements**: If you import CSV/QIF statements for both accounts independently (where dates may differ by 1–2 days due to wire settlement), Moneta's **fuzzy date-window matching engine ($\pm 3\text{ days}$)** automatically pairs the existing imported transactions together instead of creating a duplicate entry.

### C. Reconciliation Independence & Atomic VOID Protection
* **Independent Statement Reconciliation**: Reconciling the transfer leg in Account A (when Account A's statement arrives) leaves Account B's leg unreconciled until Account B's separate statement is verified.
* **Atomic Pair-Wide `VOID`**: Marking a transfer as `VOID` or un-voiding atomically updates both legs to ensure ledger balance parity.

---

## 4. Split Transactions

For transactions spanning multiple spending categories (e.g. Costco receipts, payroll with tax deductions):

1. Check the **Is Split Transaction?** box on the transaction form.
2. Add itemized line items under the **Split Details** table.
3. Moneta validates that the sum of split lines exactly equals the master transaction amount before posting.

---

## 5. Payee Intelligence (Auto-Categorization & Rules)

Moneta memorizes past payees and transaction patterns:
* Typing a payee (e.g. *Starbucks*) automatically populates the default expense category (*Food & Dining $\rightarrow$ Coffee*), default account, and tags.
* Transaction matching rules can automatically classify imported statements based on keywords and amount ranges.

---

## 6. Bank Statement Reconciliation Wizard

To reconcile your monthly bank or credit card statement against your records:

1. Click **Reconcile Statement** on the account form or dashboard.
2. Enter your **Statement Ending Date** and **Statement Ending Balance**.
3. Check off cleared deposits and payments in the interactive list.
4. The wizard updates the **Difference Indicator** in real time.
5. Once Difference reaches **$0.00**, click **Finish Reconciliation** to lock and mark transactions as Reconciled (`R`).
