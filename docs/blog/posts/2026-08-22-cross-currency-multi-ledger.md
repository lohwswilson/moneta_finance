---
date: 2026-08-22
authors:
  - wilson
categories:
  - Architecture
  - Banking
---

# Architecting Two-Legged Cross-Currency Transfers in Odoo 18

Most personal finance tools force all accounts into a single fiat currency or break when you transfer money between accounts denominated in different currencies.

<!-- more -->

## Native Multi-Currency Ledger Integrity

In Moneta, every account retains its native currency ledger. When transferring funds between a **SGD checking account** and a **USD brokerage account**:
1. **Automated Exchange Conversion**: Moneta queries Odoo's real-time currency table on the transaction date to calculate the counterpart leg.
2. **Bank Fee & Spread Tolerance**: Users can fine-tune the exact received amount in the target currency to account for wire remittance fees.
3. **Smart Matching**: Imported statements from both banks are paired automatically using a $\pm 3$-day fuzzy matching window.

Read more in our [Banking & Checkbook Register Guide](../../02_BANKING_AND_RECONCILIATION.md).
