# FIRE Analytics & Monte Carlo Wealth Simulator Guide

The **FIRE & Wealth Simulator** in Moneta Personal Finance empowers you to model long-term financial independence, calculate safe withdrawal rates, and stress-test your retirement portfolio against 1,000 randomized market timelines using **stochastic Monte Carlo modeling**.

---

## 🌟 Executive Overview: Why Traditional Spreadsheets Fail

Traditional financial plans assume a constant, linear investment return (e.g., *"My portfolio will grow by 7% every year"*). In the real world, markets are volatile. 

If a severe market crash occurs during the first 3 to 5 years of your retirement, drawing down fixed living expenses from a depleted portfolio can permanently destroy your capital—a phenomenon known as **Sequence of Returns Risk**.

```
Traditional Linear Model:    $500k ──(+7%)──> $535k ──(+7%)──> $572k ──(+7%)──> $612k  (Unrealistic)
Real World Market Volatility: $500k ──(-18%)─> $410k ──(+24%)─> $508k ──(-6%)──> $477k  (Sequence Risk)
```

Moneta's Monte Carlo simulator models **1,000 independent economic scenarios** using **Geometric Brownian Motion**, accounting for historical asset-class volatilities, cross-asset correlations, and compounding inflation.

---

## 1. 🛡️ Live Dashboard Metrics (Your Daily Indicators)

Located on your **Executive Wealth Command Center** (**Moneta** $\rightarrow$ **Dashboard**), these three metrics provide an instant pulse check on your financial freedom.

### A. Emergency Runway Buffer (Months)
Answers: *"If all income stopped today, how many months could my family survive?"*

$$\text{Emergency Runway (Months)} = \frac{\text{Liquid Cash Assets} + \text{Liquid Brokerage Holdings}}{\text{Trailing 3-Month Average Monthly Burn Rate}}$$

* **Liquid Assets**: Sum of checking, savings, money market funds, and non-retirement stock brokerage accounts (automatically converted to your base currency).
* **Monthly Burn Rate**: Computed dynamically from the last 90 days of actual categorized expense transactions (excluding internal transfers and credit card payoffs).

#### 🧭 How to Interpret Your Runway:
| Runway (Months) | Status | Financial Action |
| :--- | :--- | :--- |
| **$< 3$ Months** | 🔴 **Critical** | Build cash buffer immediately; cut discretionary spending. |
| **3 – 6 Months** | 🟡 **Standard** | Healthy buffer for stable salaried employees. |
| **6 – 12 Months** | 🟢 **Resilient** | Recommended for freelancers, business owners, and families. |
| **$> 24$ Months** | 🔵 **Cash Drag** | Excess cash sitting idle; consider investing surplus into productive index funds or bonds. |

---

### B. The 4% Rule & Your "FIRE Number"
Based on the landmark Trinity Study, the **4% Rule** calculates the nest egg required where safe portfolio withdrawals will cover 100% of your annual living expenses indefinitely without depleting principal.

$$\text{Annual Living Expenses} = \text{Monthly Burn Rate} \times 12$$

$$\text{FIRE Target Amount} = \text{Annual Living Expenses} \times 25 \quad \left( \text{i.e. } \frac{\text{Annual Expenses}}{0.04} \right)$$

$$\text{FIRE Progress \%} = \left( \frac{\text{Current Total Net Worth}}{\text{FIRE Target Amount}} \right) \times 100$$

#### 🎯 Real-World Example:
* **Monthly Expenses**: $5,000 / month
* **Annual Expenses**: $5,000 \times 12 = \$60,000 / \text{year}$
* **FIRE Target**: $\$60,000 \times 25 = \mathbf{\$1,500,000}$
* **Current Net Worth**: $750,000
* **FIRE Progress**: $\frac{\$750,000}{\$1,500,000} \times 100 = \mathbf{50.0\%}$

---

## 2. 🎲 1,000-Path Monte Carlo Wealth Simulator

The Monte Carlo engine simulates your exact financial journey across two continuous phases:
1. **Accumulation Phase**: You work, earn income, add annual savings, and compound returns.
2. **Decumulation / Retirement Phase**: You stop working and withdraw living expenses adjusted for compounding annual inflation.

---

### Step-by-Step: How to Run a Simulation

1. Navigate to **Moneta** $\rightarrow$ **Planning** $\rightarrow$ **Monte Carlo Simulator**.
2. Click **New** to create a retirement scenario.
3. Fill in your scenario parameters:

| Input Field | Description | Example Value |
| :--- | :--- | :---: |
| **Plan Name** | Label for this scenario (e.g. *Retire at 50*, *Conservative 60/40*) | `Retire at 50` |
| **Current Portfolio Value** | Total existing liquid investments and retirement savings | `$250,000` |
| **Annual Savings Contribution** | New money you save and invest each year during working years | `$24,000` |
| **Years to Retirement** | Number of working years left before you stop working | `15` |
| **Years in Retirement** | Estimated retirement lifespan to stress-test (typically 30–40 years) | `35` |
| **Annual Retirement Spending** | Desired annual living expenses in **today's purchasing power** | `$60,000` |
| **Equities Allocation (%)** | Percentage allocated to global equities/index funds (e.g. S&P 500, VWRA) | `80%` |
| **Bonds Allocation (%)** | Percentage allocated to fixed income/treasuries (auto-calculated) | `20%` |
| **Expected Inflation Rate (%)** | Annual cost-of-living inflation expectation (default: 2.5%) | `2.5%` |

4. Click the **"Run 1,000-Path Simulation"** button in the top header.
5. In ~1 second, Moneta executes all 1,000 random market paths and generates your results.

---

## 3. 📊 How to Interpret Your Simulation Results

Once the simulation completes, Moneta presents five key summary metrics and a full year-by-year percentile trajectory table.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │              MONTE CARLO PROJECTION CURVES              │
  Wealth ($)      │                                                         │
       ▲          │                                    ... P90 (Optimistic) │
       │          │                             . - ~ ~                     │
       │          │                      . - ~         ─── P50 (Median)     │
       │          │               . - ~           - - -                     │
       │          │        . - ~           - - -       ... P10 (Bear Market)│
       │          │ . - ~           - - -                                   │
       └──────────┴─────────────────────────────────────────────────────────► Time (Years)
                  │ ◄─── Accumulation ───► │ ◄──────── Retirement ────────► │
```

### A. Success Probability (%)
The percentage of the 1,000 simulated lifetimes where your money lasted throughout your entire retirement without hitting $0.

* **$\ge 95\%$ (Excellent 🟢)**: Your plan is robust. Your portfolio will survive severe historical market crashes (1929 Depression, 1970s Stagflation, 2008 GFC).
* **$80\% – 94\%$ (Solid 🟡)**: High probability of success. In the worst 10% of market environments, minor temporary spending reductions (e.g., cutting vacations by 10% during recessions) will ensure survival.
* **$65\% – 79\% (Vulnerable 🟠)**: Elevated Sequence of Returns Risk. You should increase annual savings, work 2–3 additional years, or reduce retirement spending targets.
* **$< 65\%$ (High Risk 🔴)**: Unsustainable plan. High likelihood of outliving your capital.

---

### B. The Percentile Bands ($P_{10}$, $P_{50}$, $P_{90}$)

| Metric | Economic Scenario Represented | What It Means for You |
| :--- | :--- | :--- |
| **$P_{10}$ (Conservative)** | **10th Percentile / Prolonged Bear Market** | Your portfolio's ending balance in the worst 10% of market conditions. If $P_{10} > \$0$, you are safe even in economic crises. |
| **$P_{50}$ (Median)** | **50th Percentile / Expected Average Market** | Your expected most probable wealth trajectory over time. |
| **$P_{90}$ (Optimistic)** | **90th Percentile / Secular Bull Market** | Your wealth trajectory during exceptional multi-decade market expansions. |

---

### C. Median Wealth at Retirement
Displays the estimated size of your nest egg on the exact day you transition from the **Accumulation Phase** into the **Retirement Phase**.

---

## 4. 🔬 The Mathematics Behind the Engine

For financial engineers and curious users, Moneta uses the standard **Geometric Brownian Motion (GBM)** continuous-time stochastic process:

### Asset Class Parameters:
* **Equities**: Expected nominal drift $\mu_{\text{eq}} = 9.5\%$, Volatility $\sigma_{\text{eq}} = 16.0\%$
* **Bonds / Fixed Income**: Expected nominal drift $\mu_{\text{bd}} = 4.5\%$, Volatility $\sigma_{\text{bd}} = 6.0\%$
* **Cross-Asset Correlation**: $\rho = 0.20$

### Portfolio Drift and Volatility:
$$\mu_{\text{port}} = w_{\text{eq}}\mu_{\text{eq}} + w_{\text{bd}}\mu_{\text{bd}}$$

$$\sigma_{\text{port}} = \sqrt{(w_{\text{eq}}\sigma_{\text{eq}})^2 + (w_{\text{bd}}\sigma_{\text{bd}})^2 + 2 w_{\text{eq}} w_{\text{bd}} \rho \sigma_{\text{eq}} \sigma_{\text{bd}}}$$

### Annual Stochastic Step ($t$):
For each year $t$, a random log-return is drawn from a normal distribution:
$$\text{Return}_t = \exp\left( \left(\mu_{\text{port}} - \frac{1}{2}\sigma_{\text{port}}^2\right) + \sigma_{\text{port}} \cdot Z \right), \quad \text{where } Z \sim \mathcal{N}(0, 1)$$

* **In Accumulation ($t \le Y_{\text{accum}}$)**:
  $$W_t = (W_{t-1} + \text{Annual Savings}) \times \text{Return}_t$$
* **In Retirement ($t > Y_{\text{accum}}$)**:
  $$W_t = \left(W_{t-1} - \text{Annual Spend} \times (1 + \text{Inflation})^{t - 1}\right) \times \text{Return}_t$$

---

## 5. 💡 Strategies to Improve Your Retirement Success

If your simulation returns a success probability below $90\%$, test these 4 high-leverage levers in Moneta:

1. **Increase Equity Allocation**: If your timeline is $> 15$ years, increasing equity allocation from 50% to 75–80% significantly boosts expected long-term compounding.
2. **Increase Annual Savings by 10–15%**: Boosting current annual savings exerts compounding pressure during your accumulation years.
3. **Delay Retirement by 2 Years**: Working just 2 more years has a double compounding benefit: 2 extra years of portfolio growth + 2 fewer years of portfolio withdrawals.
4. **Implement Flexible Retirement Spending**: Modeling a dynamic spending rule (withdrawing 10% less during negative market years) boosts portfolio survival rates by over $+15\%$.

---

## 6. 🏛️ Empirical Ticker History & 100-Year Crisis Stress-Testing

Beyond theoretical Gaussian distributions, Moneta supports testing against **real market history**:

### A. Personalized 10-to-20 Year Ticker History (Empirical Mode)
Instead of generic asset assumptions, Moneta extracts 10 to 20 years of monthly adjusted close prices from Yahoo Finance for your **actual portfolio holdings** (`moneta.holding`):
* Calculates your portfolio's exact empirical **CAGR**, **realized volatility ($\sigma_{\text{realized}}$)**, and **cross-ticker covariance matrix**.
* Distinguishes between an all-market index portfolio (`VOO`, `VWRA`) versus high-beta growth stocks or dividend-heavy aristocrats.

### B. 100-Year Historical Crisis Replay Mode
Replays your retirement plan through real historical market shocks:

| Historical Era | Real Market Event | Stress-Test Focus |
| :--- | :--- | :--- |
| **1929 Great Crash** | $-86\%$ Real equity drawdown over 3 years | Deflationary depression survival |
| **1973–1974 Stagflation** | $+12\%$ Inflation spike with negative real asset returns | Purchasing power erosion |
| **1987 Black Monday** | Single-day $-22.6\%$ liquidity shock | Recovery resilience |
| **2000–2002 Dot-Com Bust** | 3 consecutive negative equity years | Early retirement Sequence of Returns Risk |
| **2008 Global Financial Crisis** | $-50\%$ Global equity shock + housing contraction | Liquidity runway and buffer durability |
| **2020 Pandemic Shock** | Rapid $-34\%$ crash followed by fast inflationary rebound | Volatility whip-saw resistance |

