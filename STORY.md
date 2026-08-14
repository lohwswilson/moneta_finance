# The Story Behind Moneta Personal Finance

### From Microsoft Money to Quicken to Odoo 18

Years ago, I was a dedicated user of **Microsoft Money**. It was reliable, comprehensive, and gave me complete visibility over my personal finances. But when Microsoft discontinued it, I had to migrate to **Quicken**.

Over time, commercial financial software shifted towards closed cloud ecosystems, steep monthly subscription models, and bloated interfaces. My personal wealth was scattered:
* Checking and high-yield savings in local banks
* International equities and ETFs in USD/SGD brokerage accounts
* Real estate and mortgages in spreadsheets
* FIRE calculations on scratchpads

### The Developer's Realization

Having spent several years developing enterprise business systems on **Odoo**, I realized that the Odoo framework provides the exact architecture required for the ultimate personal finance system:

1. **Enterprise-Grade Double-Entry & Running Balance Math**: Exact point-in-time balances without floating-point drift.
2. **True Multi-Currency Support**: Real-time conversion of foreign stocks (USD) to home currency (SGD) with historical exchange rates.
3. **100% Data Sovereignty**: Running on your own PostgreSQL database, with zero telemetry, zero advertising, and zero subscription paywalls.

### The Weekend Kickoff

One weekend, I sat down and began coding the foundation: bringing back the beloved checkbook registers and split transactions of Microsoft Money, combined with Quicken's investment tracking, and wrapped in the visual elegance of modern fintech platforms like Copilot Money and Maybe.

What started as a weekend project to solve my own financial tracking needs has grown into **Moneta Personal Finance**.

### Why Open Source?

Financial data is the most personal data you own. You shouldn't have to surrender your privacy or pay a perpetual subscription just to know your net worth or balance a checkbook.

I’ve open-sourced Moneta for the global community. Whether you're an ex-Microsoft Money user, a Quicken migrant, an Odoo enthusiast, or someone working toward Financial Independence (FIRE), you are warmly invited to contribute, suggest features, or simply enjoy using it.

— **Wilson Loh** ([@lohwswilson](https://github.com/lohwswilson))
