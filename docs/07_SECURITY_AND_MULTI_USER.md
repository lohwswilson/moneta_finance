# Multi-User Privacy, Joint Accounts & Security

Moneta is built from the ground up to support family households, joint accounts, and confidential wealth data isolation.

---

## 1. Record-Level Data Isolation

* **Private by Default**: All accounts, transactions, investments, and budgets are filtered by `user_id = self.env.user.id`.
* Users cannot see another user's personal financial accounts unless explicitly shared.

---

## 2. Joint Accounts & Household Sharing

You can grant spouses or partners access to specific accounts:

* **Permission Tiers**:
  1. `read`: View-only access to balance and registers.
  2. `write`: Can add transactions and reconcile.
  3. `full`: Full administrative permissions.
* **Net Worth Inclusion**: Co-owners can toggle whether joint accounts are included in their personal net worth calculations.

---

## 3. Emergency Digital Estate Access

Assign trusted emergency contacts with configurable security lock periods (e.g. 30-day waiting period with notification) to ensure your family can access financial records if unexpected life events occur.
