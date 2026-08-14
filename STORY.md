# The Story Behind the Moneta Odoo Module

### From Microsoft Money to Quicken to Odoo 18

Years ago, I was a dedicated user of **Microsoft Money**. It was reliable, simple, and gave me complete visibility over my personal finances. But when Microsoft discontinued it, I had to migrate to **Quicken**.

Over time, commercial financial software shifted toward closed cloud ecosystems and steep monthly subscription models. My personal finances were scattered:
* Checking and savings in local banks
* International equities in foreign currency brokerage accounts
* Real estate and mortgages in spreadsheets

### The Developer's Realization

Having spent several years developing business solutions on **Odoo**, I realized that Odoo already provides the exact foundation needed for personal money management:

1. **Robust Relational Data**: Exact running balance ledger calculations with zero floating-point errors.
2. **True Multi-Currency Engine**: Converting foreign stock holdings (USD) to home currency (SGD) with historical exchange rates.
3. **Self-Hosted & Private**: Running directly on your own Odoo instance and PostgreSQL database without third-party subscriptions.

### A Weekend Project

One weekend, I sat down and started building this Odoo module: combining the straightforward checkbook registers of Microsoft Money with live stock quote syncing and a clean modern dashboard.

What started as a weekend project for my own day-to-day finances is now **Moneta Personal Finance**.

If you're already running Odoo for your business, homelab, or personal projects, you can simply drop this module into your addons folder and manage your personal finances in the same environment.

— **Wilson Loh** ([@lohwswilson](https://github.com/lohwswilson))
