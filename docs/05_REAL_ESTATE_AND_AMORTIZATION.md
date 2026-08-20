# Real Estate, Tangible Assets & Loan Amortization

Moneta provides end-to-end management for illiquid physical assets and debt amortization schedules.

---

## 1. Real Estate & Tangible Assets

Track your physical property and luxury tangible assets:

* **Asset Types**: Primary Residence, Rental Properties, Commercial Real Estate, Vehicles, Fine Art & Antiques, Jewelry.
* **Valuation History**: Track professional appraisals over time.
* **Mortgage Linkage**: Link mortgages to specific properties to calculate **Net Real Estate Equity**:

$$\text{Net Home Equity} = \text{Current Market Valuation} - \text{Outstanding Mortgage Debt}$$

$$\text{Loan-to-Value (LTV)} = \left( \frac{\text{Outstanding Mortgage Debt}}{\text{Market Valuation}} \right) \times 100$$

---

## 2. Loan & Mortgage Amortization Engine

Simulate repayment strategies and analyze interest savings:

* **Monthly Amortization Schedule**: Calculates monthly Principal vs. Interest breakdown using standard compound interest formulas.
* **Prepayment Scenarios**: Test recurring or one-time lump-sum extra principal payments.
* **Savings Metrics**: Real-time display of total interest saved ($) and loan payoff acceleration (months shaved off).

---

## 3. Direct Loan & Mortgage Account Integration

Loan and mortgage accounts (`moneta.account`) directly surface amortization intelligence:
* **Account Card Metrics**: The form header and kanban cards display:
  - **Monthly Payment (P&I)**: Required base monthly debt service.
  - **Estimated Payoff Date**: Projected mortgage freedom date accounting for extra principal prepayments.
  - **Remaining Total Interest**: Lifetime interest obligation.
* **1-Click Amortization Shortcut**: Click **Amortization** directly on any loan card or stat button to inspect or create the linked amortization scenario.
