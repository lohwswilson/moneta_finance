# Singapore 🇸🇬

Moneta Personal Finance provides comprehensive, native localization for Singapore wealth architectures.

---

## 1. Singapore Pension Architecture: CPF & SRS

### Central Provident Fund (CPF) Accounts
Moneta models all four core CPF account types with their respective interest rates and lowest-balance compounding rules:

* **CPF Ordinary Account (`cpf_oa`)**: Base interest rate of **2.50% p.a.** used for housing, insurance, and CPFIS investments.
* **CPF Special Account (`cpf_sa`)**: Base interest rate of **4.00% p.a.** for retirement accumulation.
* **CPF MediSave Account (`cpf_ma`)**: Base interest rate of **4.00% p.a.** for hospitalization and approved medical insurance up to the Basic Healthcare Sum (BHS).
* **CPF Retirement Account (`cpf_ra`)**: Created at age 55, base interest rate of **4.00% p.a.** to fund lifelong payouts under CPF LIFE.

### Lowest-Balance Monthly Interest Calculation
In Singapore, CPF interest is computed monthly based on the **lowest end-of-day balance of that calendar month** and credited annually on December 31. Moneta's interest engine simulates this exact rule across all 12 months.

### CPF LIFE Retirement Payout Simulator
* Simulates lifelong monthly income across the **Standard Plan** (level payouts), **Escalating Plan** (+2% annual increase), and **Basic Plan** (lower payout, higher bequest).
* Benchmarks projections against Singapore retirement sum milestones (**BRS**: $106,500, **FRS**: $213,000, **ERS**: $426,000).
* Accounts for the +7% per year payout bonus for deferring start age from 65 up to 70.

### Supplementary Retirement Scheme (SRS)
* Tracks annual voluntary contribution caps (**SGD $15,300** for Singapore Citizens/PRs, **SGD $35,700** for Foreigners).
* Computes instant IRAS income tax savings across all progressive marginal tax brackets (0% to 24%).
* Models the **10-year penalty-free withdrawal window** post-statutory retirement age with **50% tax exemption** (e.g. withdrawing up to $40,000/year results in $0 income tax).

---

## 2. Singapore Real Estate, Housing Loans & Stamp Duties

### CPF Housing Accrued Interest Engine
When using CPF OA funds to buy a property:
* Compounding 2.50% annual interest on downpayment, housing grants, and monthly mortgage payments is tracked over the holding period.
* **Resale Proceeds & Negative Sale Detector**: Calculates gross sales proceeds, bank/HDB loan payoff, total CPF refund due to OA, and **net cash in hand**.

### Buyer's Stamp Duty (BSD) & Additional Buyer's Stamp Duty (ABSD)
* **Progressive Residential BSD**: 1% (1st $180k), 2% (2nd $180k), 3% (next $640k), 4% (next $500k), 5% (next $1.5m), 6% (> $3.0m).
* **ABSD Matrix**: Automatically applies 0%/20%/30% for Citizens, 5%/30%/35% for PRs, 60% for Foreigners, and 65% for Entities.

### Regulatory Affordability: TDSR & MSR
* **Total Debt Servicing Ratio (TDSR $\le 55\%$)**: Ensures total monthly debt obligations do not exceed 55% of gross monthly income.
* **Mortgage Servicing Ratio (MSR $\le 30\%$)**: Enforces the 30% monthly cap for HDB flats and Executive Condominiums (ECs).
* **Mortgage Comparator**: Compares **HDB Concessionary (2.60%)**, **Bank SORA**, and **MAS 4.0% Regulatory Stress Test** payments side-by-side.

---

## 3. Government Bonds (SSB / T-Bills) & Global UCITS Advantage

### Singapore Savings Bonds (SSB)
* Models 10-year step-up interest schedules, semi-annual coupons, $200k individual holding limits, and monthly par redemption with the $2 MAS fee.

### MAS Treasury Bills (T-Bills)
* Supports 6-Month and 1-Year T-Bills via discount auction accounting. Computes actual investment cost, net discount profit at maturity, and annualized cut-off yield (% p.a.).

### Irish-Domiciled UCITS ETFs (`CSPX.L`, `VWRA.L`, `SWRD.L`)
* **15% vs. 30% Dividend Withholding Tax**: Demonstrates the 15% tax drag advantage of Irish UCITS ETFs over US-domiciled equivalents (`VOO`/`VTI`) for non-US investors.
* **0% US Estate Tax**: Avoids up to 40% US Estate Tax on holdings exceeding $60,000.

---

## 4. IRAS Personal Income Tax Planner & Optimization

* **Progressive Tax Brackets**: Full YA 2024–2026 progressive rate table (0% to 24%).
* **$80,000 Personal Relief Cap**: Tracks Earned Income, CPF Employee, RSTU (Self $8k + Loved Ones $8k), SRS ($15.3k), NSman, Child, and Parent reliefs.
* **250% Charitable Donations**: IPC donations are exempt from the $80k cap and provide 2.5x tax deduction.
* **Year-End Optimization Advisory**: Proactively suggests actionable top-ups (RSTU, SRS, donations) before December 31.
