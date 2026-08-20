# Banking, Checkbook Registers & Statement Reconciliation

Moneta incorporates the battle-tested checkbook register architecture of **Quicken Premier** with real-time running balance recalculation and interactive bank statement reconciliation.

---

## 1. Color-Coded Account Dashboard

Accounts are visually categorized with color accents and metrics:

* 🟢 **Emerald Green Cards (Cash & Bank Accounts)**: Shows available cash, cleared balance, and quick reconcile links.
* 🔵 **Royal Blue Cards (Brokerage & Stock Accounts)**: Shows live stock market value, uninvested cash, and total return %.
* 🟣 **Royal Purple Cards (Credit Cards)**: Shows current card balance, credit limit, and statement due date.
* 🔴 **Crimson Red Cards (Loans & Mortgages)**: Shows outstanding principal debt and active loan status.

---

## 2. Checkbook Register & Running Balances

When opening any account, the **Register & Transactions** tab displays an interactive ledger:

* **Chronological Ordering & Tiebreakers**: Sorted chronologically with credit-before-debit tiebreaking (`transaction_date desc, amount asc, id desc`). On identical dates and import timestamps, deposits/credits are listed before debits/payments so running balances never dip negative on same-day funded purchases.
* **Running Balance Calculation**: Automatically computes the exact point-in-time account balance across all historical rows using high-performance SQL window partitions.
* **1-Click `Clr` Toggle**:
  Clicking the `Clr` button on any row toggles its reconciliation status:
  $$\text{Unreconciled (Empty)} \longrightarrow \text{Cleared (🔵 Clr)} \longrightarrow \text{Reconciled (🟢 R)}$$

---

## 3. Account Transfers & Reconciliation Independence

When transferring funds between two tracked accounts:
* **Automatic Counterpart Leg**: Creating a transfer in Checking automatically creates the mirrored counterpart leg in Savings (with negated sign and reverse link).
* **Independent Statement Reconciliation**: Reconciling the transfer leg in Account A (when Account A's statement arrives) leaves Account B's leg unreconciled until Account B's separate statement is verified.
* **Pair-Wide VOID**: Marking a transfer as `VOID` or un-voiding atomically updates both legs to ensure ledger balance parity.

---

## 4. Split Transactions

For transactions with multiple spending categories (e.g. Costco / Supermarket receipts):

1. Check the **Is Split Transaction?** box on the transaction form.
2. Add line items under the **Split Details** table.
3. Moneta validates that the sum of line amounts exactly equals the master transaction amount before posting.

---

## 5. Payee Intelligence (Auto-Categorization)

Moneta memorizes past payees and transaction descriptions:
* Typing a payee (e.g. *Starbucks*) automatically populates the default expense category (*Food & Dining $\rightarrow$ Coffee*), default account, and tags.
* Wildcard matching rules can automatically classify imported statements.

---

## 6. Bank Statement Reconciliation Wizard

To reconcile your monthly bank or credit card statement:

1. Click **Reconcile Statement** on the account form or dashboard.
2. Enter your **Statement Ending Date** and **Statement Ending Balance**.
3. Check off cleared deposits and payments in the interactive list.
4. The wizard updates the **Difference Indicator** in real time.
5. Once Difference reaches **$0.00**, click **Finish Reconciliation** to lock and mark transactions as Reconciled (`R`).
