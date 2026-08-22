# Malaysia Financial & Tax Pack 🇲🇾

Moneta Personal Finance includes a dedicated regional satellite module — **`moneta_finance_malaysia`** ("Malaysia Wealth & Tax") — providing native compliance and wealth tooling for the Malaysian financial ecosystem.

---

## 1. EPF / KWSP 3-Account Restructuring Hub

Moneta models the modern Employees Provident Fund (*Kumpulan Wang Simpanan Pekerja*) 3-account retirement structure:

| Account Type | Allocation % | Purpose | Statutory Withdrawal Rules |
| :--- | :---: | :--- | :--- |
| **Akaun Persaraan (Account 1)** | **75%** | Long-term retirement accumulation | Locked until statutory retirement age (55/60). |
| **Akaun Sejahtera (Account 2)** | **15%** | Life-stage wellbeing | Pre-retirement withdrawals for housing, healthcare, and education. |
| **Akaun Fleksibel (Account 3)** | **10%** | Short-term emergency liquidity | 1-Click flexible anytime withdrawals ($> \text{RM } 50$). |

### EPF Compounding Interest & Dividend Engine
* **Annual Dividend Crediting**: Simulates annual EPF dividend declarations (Simpanan Konvensional vs. Simpanan Shariah) with daily rest compounding.
* **i-Saraan Matching & Voluntary Contributions**: Tracks self-employed voluntary top-ups and annual government matching incentives (up to RM 500/year).

---

## 2. LHDN Borang BE Personal Income Tax Relief Planner

Moneta features a real-time personal income tax calculator and relief optimizer for Malaysian tax residents filing **Borang BE**:

### Key Tax Relief Categories Modeled:
1. **Individual & Dependent Relatives**: RM 9,000 standard individual relief.
2. **Medical & Healthcare**: Up to RM 10,000 for serious diseases, complete medical exams, and dental care.
3. **Lifestyle & Tech**: Up to RM 2,500 for books, laptops, smartphones, home internet subscriptions, and gym memberships.
4. **Sports Equipment & Activities**: Additional RM 1,000 sports equipment and training fees relief.
5. **SSPN (National Education Savings Scheme)**: Up to RM 8,000 net annual deposit deduction.
6. **EPF Employee & Life Insurance**: Up to RM 4,000 for mandatory/voluntary EPF + RM 3,000 for life insurance premiums.
7. **Private Retirement Scheme (PRS)**: Up to RM 3,000 relief for voluntary PRS contributions.
8. **Electric Vehicle (EV) Charging Facilities**: Up to RM 2,500 for home EV charger installation and subscription costs.

> **Year-End Tax Optimization Advisory**: Moneta audits your current year expenses against statutory relief ceilings and proactively recommends tax-deductible actions before December 31.

---

## 3. Semi-Flexi & Full-Flexi Home Loan SBR Simulator

Malaysian banks offer Semi-Flexi and Full-Flexi housing loans pegged to the **Standard Base Rate (SBR)**:

* **Daily Rest Interest Math**:
  $$\text{Daily Interest} = \frac{(\text{Outstanding Principal} - \text{Flexi Current Account Deposit}) \times (\text{SBR} + \text{Spread})}{365}$$
* **Interest Savings & Loan Acceleration**: Calculates the exact lifetime interest saved and months shaved off the mortgage by parking surplus cash in the linked Flexi current account.

---

## 4. Private Retirement Scheme (PRS) & ASNB Unit Trusts

* **PRS Fund Performance**: Tracks Private Retirement Scheme fund NAVs, asset allocation (Growth, Moderate, Conservative), and computes tax savings.
* **ASNB Fixed-Price Funds (ASB, ASM)**: Tracks capital-protected fixed-price unit trusts (RM 1.00/unit), dividend income declarations, and reinvestment shares.

---

## 5. Real Property Gains Tax (RPGT) Disposal Calculator

Calculates Malaysian capital gains tax on property disposals based on holding duration:

| Disposal Horizon | Malaysian Citizens / PRs | Non-Citizens / Foreigners | Companies |
| :--- | :---: | :---: | :---: |
| **Within 3 Years** | 30% | 30% | 30% |
| **In the 4th Year** | 20% | 30% | 20% |
| **In the 5th Year** | 15% | 30% | 15% |
| **Beyond 5 Years** | **0% (Exempt)** | 10% | 10% |

* **Allowable Expenses**: Automatically factors in stamp duty, legal fees, agent commissions, and capital improvement renovations into the cost base.

---

## 6. Pre-Loaded Malaysian Master Data

Includes pre-seeded financial institutions and common payees:
* **Banks**: Maybank, CIMB Bank, Public Bank, RHB, Hong Leong Bank, AmBank, Alliance Bank.
* **Digital Banks**: GXBank, Boost Bank, AEON Bank.
* **E-Wallets & Utilities**: Touch 'n Go eWallet, GrabPay, BigPay, TNB (Tenaga Nasional), Air Selangor, Indah Water, TM Unifi, Maxis, CelcomDigi.
