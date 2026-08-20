# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import http, fields
from odoo.http import request


class MonetaMCPController(http.Controller):

    @http.route('/moneta/mcp/tools', type='json', auth='user', methods=['POST', 'GET'])
    def get_tools(self):
        """Returns the list of available MCP tools and JSON schemas."""
        tools = [
            {
                "name": "moneta_get_net_worth",
                "description": "Get current executive net worth summary, liquid cash, investment market value, and total liabilities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "moneta_list_accounts",
                "description": "List all financial accounts (cash, bank, credit card, loan, investment) with current and cleared balances.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "account_type": {
                            "type": "string",
                            "enum": ["checking", "savings", "cash", "credit", "loan", "mortgage", "brokerage", "retirement", "crypto"],
                            "description": "Optional filter by account type"
                        }
                    }
                }
            },
            {
                "name": "moneta_get_transactions",
                "description": "Retrieve recent transactions with payee names, amounts, categories, and reconciliation states.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "account_name": {"type": "string", "description": "Optional account name"},
                        "limit": {"type": "integer", "default": 20, "description": "Maximum number of transactions to return"},
                        "category_name": {"type": "string", "description": "Optional category name filter"}
                    }
                }
            },
            {
                "name": "moneta_create_transaction",
                "description": "Record a new expense, income, or transfer transaction in Moneta Finance.",
                "inputSchema": {
                    "type": "object",
                    "required": ["account_name", "amount", "payee_name"],
                    "properties": {
                        "account_name": {"type": "string", "description": "Name of the account to post transaction to"},
                        "amount": {"type": "number", "description": "Transaction amount (negative for expenses, positive for deposits)"},
                        "payee_name": {"type": "string", "description": "Payee or merchant name"},
                        "category_name": {"type": "string", "description": "Spending or income category"},
                        "transaction_date": {"type": "string", "description": "Date formatted YYYY-MM-DD (defaults to today)"},
                        "memo": {"type": "string", "description": "Optional memo or description"}
                    }
                }
            },
            {
                "name": "moneta_get_budgets",
                "description": "Get envelope budget statuses, allocated amounts, actual spending, and remaining allowances for the active period.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "moneta_get_upcoming_bills",
                "description": "Get upcoming recurring bills, subscriptions, and scheduled transactions due in the next N days.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "default": 14, "description": "Number of days forward to look"}
                    }
                }
            },
            {
                "name": "moneta_simulate_loan_payoff",
                "description": "Simulate mortgage or loan early payoff with extra monthly or lump-sum prepayments.",
                "inputSchema": {
                    "type": "object",
                    "required": ["principal", "annual_rate", "term_years"],
                    "properties": {
                        "principal": {"type": "number", "description": "Principal loan balance"},
                        "annual_rate": {"type": "number", "description": "Annual interest rate in percentage (e.g. 5.5 for 5.5%)"},
                        "term_years": {"type": "integer", "description": "Original loan term in years (e.g. 30, 25, 15)"},
                        "extra_monthly": {"type": "number", "default": 0.0, "description": "Extra monthly principal payment"},
                        "lump_sum": {"type": "number", "default": 0.0, "description": "One-time lump sum prepayment"}
                    }
                }
            },
            {
                "name": "moneta_undo_last_action",
                "description": "1-Click undo / rollback of the most recent user action (e.g. accidental transaction create, import, or batch edit).",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        return {"tools": tools}

    @http.route('/moneta/mcp/call', type='json', auth='user', methods=['POST'])
    def call_tool(self, name, arguments=None):
        """Executes an MCP tool against Moneta models."""
        env = request.env
        args = arguments or {}

        if name == "moneta_get_net_worth":
            accounts = env['moneta.account'].search([])
            assets = sum(a.current_balance for a in accounts if a.current_balance > 0)
            liabs = sum(abs(a.current_balance) for a in accounts if a.current_balance < 0)
            holdings = env['moneta.holding'].search([])
            stock_val = sum(h.market_value for h in holdings)
            props = env['moneta.property'].search([])
            prop_val = sum(p.current_valuation for p in props)
            total_net_worth = assets + stock_val + prop_val - liabs
            return {
                "total_net_worth": round(total_net_worth, 2),
                "liquid_cash_and_bank": round(assets, 2),
                "investment_market_value": round(stock_val, 2),
                "property_and_valuables": round(prop_val, 2),
                "total_liabilities": round(liabs, 2),
                "currency": env.company.currency_id.name,
            }

        elif name == "moneta_list_accounts":
            domain = []
            if args.get('account_type'):
                domain.append(('account_type', '=', args['account_type']))
            accounts = env['moneta.account'].search(domain)
            return {
                "accounts": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "account_type": a.account_type,
                        "current_balance": a.current_balance,
                        "cleared_balance": a.cleared_balance,
                        "currency": a.currency_id.name,
                    }
                    for a in accounts
                ]
            }

        elif name == "moneta_get_transactions":
            domain = [('state', '!=', 'void')]
            if args.get('account_name'):
                domain.append(('account_id.name', 'ilike', args['account_name']))
            if args.get('category_name'):
                domain.append(('category_id.name', 'ilike', args['category_name']))
            limit = args.get('limit', 20)
            txs = env['moneta.transaction'].search(domain, order='transaction_date desc, id desc', limit=limit)
            return {
                "transactions": [
                    {
                        "id": t.id,
                        "date": str(t.transaction_date),
                        "account": t.account_id.name,
                        "payee": t.payee_id.name or t.payee_name or '',
                        "category": t.category_id.display_name or 'Uncategorized',
                        "amount": t.amount,
                        "state": t.state,
                        "memo": t.memo or '',
                    }
                    for t in txs
                ]
            }

        elif name == "moneta_create_transaction":
            acc_name = args.get('account_name')
            account = env['moneta.account'].search([('name', 'ilike', acc_name)], limit=1)
            if not account:
                return {"error": f"Account '{acc_name}' not found."}

            payee_name = args.get('payee_name')
            payee = env['moneta.payee']._resolve_by_name(payee_name)
            if not payee and payee_name:
                payee = env['moneta.payee'].create({'name': payee_name})

            cat_id = False
            if args.get('category_name'):
                cat = env['moneta.category'].search([('name', 'ilike', args['category_name'])], limit=1)
                if cat:
                    cat_id = cat.id
            elif payee and payee.default_category_id:
                cat_id = payee.default_category_id.id

            tx_vals = {
                'account_id': account.id,
                'amount': float(args.get('amount', 0.0)),
                'payee_id': payee.id if payee else False,
                'category_id': cat_id,
                'memo': args.get('memo') or '',
            }
            if args.get('transaction_date'):
                tx_vals['transaction_date'] = args['transaction_date']

            tx = env['moneta.transaction'].create(tx_vals)
            
            # Log action for undo
            env['moneta.action.history'].log_action(
                description=f"Created transaction {payee.name if payee else ''} ({tx.amount}) via MCP",
                entity_type='transaction',
                action='create',
                entity_id=tx.id,
                after_data={'ids': [tx.id]},
            )

            return {
                "success": True,
                "transaction_id": tx.id,
                "amount": tx.amount,
                "account": account.name,
                "payee": payee.name if payee else '',
                "category": tx.category_id.name if tx.category_id else 'Uncategorized',
                "date": str(tx.transaction_date),
            }

        elif name == "moneta_get_budgets":
            budgets = env['moneta.budget'].search([('active', '=', True)])
            res = []
            for b in budgets:
                res.append({
                    "budget_name": b.name,
                    "categories": [
                        {
                            "category": c.category_id.name,
                            "budget_amount": c.amount,
                            "spent_amount": c.spent_amount,
                            "percent_spent": c.percent_spent,
                        }
                        for c in b.category_ids
                    ]
                })
            return {"budgets": res}

        elif name == "moneta_get_upcoming_bills":
            days = args.get('days', 14)
            recurring = env['moneta.recurring.transaction'].search([('active', '=', True)])
            today = fields.Date.context_today(env.user)
            future = today + timedelta(days=days)
            bills = []
            for r in recurring:
                if r.next_date and today <= r.next_date <= future:
                    bills.append({
                        "name": r.name,
                        "next_date": str(r.next_date),
                        "amount": r.amount,
                        "account": r.account_id.name,
                        "frequency": r.frequency,
                    })
            return {"upcoming_bills": bills}

        elif name == "moneta_simulate_loan_payoff":
            P = float(args.get('principal', 0.0))
            r_annual = float(args.get('annual_rate', 0.0)) / 100.0
            term_yrs = int(args.get('term_years', 30))
            extra_m = float(args.get('extra_monthly', 0.0))
            lump = float(args.get('lump_sum', 0.0))
            n = term_yrs * 12
            r = r_annual / 12.0

            pmt = (P * (r * ((1 + r) ** n)) / (((1 + r) ** n) - 1)) if r > 0 else (P / n)

            # Simulate
            bal = P
            months = 0
            act_interest = 0.0
            while bal > 0.01 and months < 1200:
                months += 1
                interest = bal * r
                act_interest += interest
                prin = min(pmt - interest + extra_m + (lump if months == 1 else 0.0), bal)
                bal -= prin

            return {
                "standard_monthly_payment": round(pmt, 2),
                "accelerated_months": months,
                "accelerated_years": round(months / 12.0, 1),
                "months_saved": max(n - months, 0),
                "years_saved": round(max(n - months, 0) / 12.0, 1),
                "total_interest_paid": round(act_interest, 2),
            }

        elif name == "moneta_undo_last_action":
            return env['moneta.action.history'].action_undo_last()

        return {"error": f"Tool '{name}' not found."}
