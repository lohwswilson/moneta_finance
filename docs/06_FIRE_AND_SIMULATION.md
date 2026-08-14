# FIRE Analytics & Monte Carlo Wealth Simulator

Moneta includes financial independence modeling and retirement probability analysis.

---

## 1. Financial Runway Buffer

Calculates how many months you can sustain your current standard of living with zero active income:

$$\text{Emergency Runway (Months)} = \frac{\text{Liquid Cash Assets} + \text{Liquid Investment Assets}}{\text{3-Month Average Monthly Burn Rate}}$$

---

## 2. The 4% Rule FIRE Milestone

Moneta computes your progress toward complete Financial Independence (FIRE) using the Trinity Study 4% Safe Withdrawal Rule:

$$\text{Annual Expenses} = \text{Monthly Burn Rate} \times 12$$

$$\text{FIRE Target Amount} = \text{Annual Expenses} \times 25$$

$$\text{FIRE Progress \%} = \left( \frac{\text{Total Net Worth}}{\text{FIRE Target Amount}} \right) \times 100$$

---

## 3. 1,000-Path Monte Carlo Wealth Simulator

Simulate 1,000 randomized market trajectories over 10 to 40 years:

* **Stochastic Returns**: Uses Geometric Brownian Motion with configurable expected returns and historical standard deviation (volatility).
* **Percentile Bands**: Displays $P_{10}$ (Conservative), $P_{50}$ (Median), and $P_{90}$ (Optimistic) wealth trajectories.
* **Success Probability**: Calculates the exact probability of your portfolio outliving retirement withdrawals.
