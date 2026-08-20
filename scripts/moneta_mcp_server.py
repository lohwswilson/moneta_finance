#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moneta Personal Finance - Model Context Protocol (MCP) Server
==============================================================
Standard JSON-RPC 2.0 stdio server implementing the Model Context Protocol (MCP)
for pairing local AI assistants (Claude Desktop, Cursor, Antigravity, Gemini)
with your Moneta Finance wealth database.

Supported Tools:
  - moneta_get_net_worth
  - moneta_list_accounts
  - moneta_get_transactions
  - moneta_create_transaction
  - moneta_get_budgets
  - moneta_get_upcoming_bills
  - moneta_simulate_loan_payoff
  - moneta_undo_last_action
"""
import sys
import json
import os
import argparse
import xmlrpc.client
from datetime import datetime, timedelta

TOOLS = [
    {
        "name": "moneta_get_net_worth",
        "description": "Get overall net worth summary, liquid cash/bank balances, investment portfolio market value, and total liabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "moneta_list_accounts",
        "description": "List all financial accounts (checking, savings, credit cards, loans, mortgages, brokerage) with current and cleared balances.",
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
        "description": "Retrieve recent transactions with payee names, amounts, categories, memos, and reconciliation statuses.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string", "description": "Optional account name filter"},
                "limit": {"type": "integer", "default": 20, "description": "Maximum number of transactions to return"},
                "category_name": {"type": "string", "description": "Optional category name filter"}
            }
        }
    },
    {
        "name": "moneta_create_transaction",
        "description": "Record a new expense, income, or transfer transaction in Moneta Finance with auto-payee matching.",
        "inputSchema": {
            "type": "object",
            "required": ["account_name", "amount", "payee_name"],
            "properties": {
                "account_name": {"type": "string", "description": "Name of the account to post to"},
                "amount": {"type": "number", "description": "Amount (negative for expenses e.g. -45.50, positive for income e.g. 5000.00)"},
                "payee_name": {"type": "string", "description": "Merchant or payee name"},
                "category_name": {"type": "string", "description": "Optional category name"},
                "transaction_date": {"type": "string", "description": "Date YYYY-MM-DD (defaults to today)"},
                "memo": {"type": "string", "description": "Optional memo"}
            }
        }
    },
    {
        "name": "moneta_get_budgets",
        "description": "Get envelope budget statuses, allocated amounts, actual spending, and remaining allowances.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "moneta_get_upcoming_bills",
        "description": "Get upcoming recurring bills and subscriptions due in the next N days.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 14, "description": "Number of days forward to look"}
            }
        }
    },
    {
        "name": "moneta_simulate_loan_payoff",
        "description": "Simulate mortgage / loan early payoff with extra monthly or lump-sum prepayments.",
        "inputSchema": {
            "type": "object",
            "required": ["principal", "annual_rate", "term_years"],
            "properties": {
                "principal": {"type": "number", "description": "Principal loan balance"},
                "annual_rate": {"type": "number", "description": "Annual interest rate % (e.g. 5.5)"},
                "term_years": {"type": "integer", "description": "Loan term in years (e.g. 30)"},
                "extra_monthly": {"type": "number", "default": 0.0, "description": "Extra monthly principal payment"},
                "lump_sum": {"type": "number", "default": 0.0, "description": "Lump sum prepayment"}
            }
        }
    },
    {
        "name": "moneta_undo_last_action",
        "description": "1-Click undo / rollback of the most recent user action in Moneta Finance.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


class MonetaClient:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def execute_kw(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kwargs)


def handle_request(client, req):
    msg_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS}
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "moneta_get_net_worth":
                accounts = client.execute_kw('moneta.account', 'search_read', [], ['name', 'account_type', 'current_balance'])
                assets = sum(a['current_balance'] for a in accounts if a['current_balance'] > 0)
                liabs = sum(abs(a['current_balance']) for a in accounts if a['current_balance'] < 0)
                holdings = client.execute_kw('moneta.holding', 'search_read', [], ['market_value'])
                stock_val = sum(h['market_value'] for h in holdings)
                props = client.execute_kw('moneta.property', 'search_read', [], ['current_valuation'])
                prop_val = sum(p['current_valuation'] for p in props)
                total_nw = assets + stock_val + prop_val - liabs
                res = {
                    "total_net_worth": round(total_nw, 2),
                    "liquid_cash_and_bank": round(assets, 2),
                    "investment_market_value": round(stock_val, 2),
                    "property_and_valuables": round(prop_val, 2),
                    "total_liabilities": round(liabs, 2),
                }

            elif tool_name == "moneta_list_accounts":
                domain = []
                if arguments.get("account_type"):
                    domain.append(('account_type', '=', arguments['account_type']))
                accounts = client.execute_kw('moneta.account', 'search_read', domain, ['name', 'account_type', 'current_balance', 'cleared_balance'])
                res = {"accounts": accounts}

            elif tool_name == "moneta_get_transactions":
                domain = [('state', '!=', 'void')]
                if arguments.get("account_name"):
                    domain.append(('account_id.name', 'ilike', arguments['account_name']))
                if arguments.get("category_name"):
                    domain.append(('category_id.name', 'ilike', arguments['category_name']))
                limit = arguments.get("limit", 20)
                txs = client.execute_kw('moneta.transaction', 'search_read', domain, ['transaction_date', 'account_id', 'payee_id', 'payee_name', 'category_id', 'amount', 'state', 'memo'], limit=limit, order='transaction_date desc, id desc')
                res = {"transactions": txs}

            elif tool_name == "moneta_create_transaction":
                acc_name = arguments.get("account_name")
                acc_ids = client.execute_kw('moneta.account', 'search', [[('name', 'ilike', acc_name)]], limit=1)
                if not acc_ids:
                    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": f"Account '{acc_name}' not found"}}

                payee_name = arguments.get("payee_name")
                payee_ids = client.execute_kw('moneta.payee', 'search', [[('name', 'ilike', payee_name)]], limit=1)
                if not payee_ids and payee_name:
                    payee_id = client.execute_kw('moneta.payee', 'create', [{'name': payee_name}])
                else:
                    payee_id = payee_ids[0] if payee_ids else False

                cat_id = False
                if arguments.get("category_name"):
                    cat_ids = client.execute_kw('moneta.category', 'search', [[('name', 'ilike', arguments['category_name'])]], limit=1)
                    if cat_ids:
                        cat_id = cat_ids[0]

                tx_vals = {
                    'account_id': acc_ids[0],
                    'amount': float(arguments.get('amount', 0.0)),
                    'payee_id': payee_id,
                    'category_id': cat_id,
                    'memo': arguments.get('memo') or '',
                }
                if arguments.get("transaction_date"):
                    tx_vals['transaction_date'] = arguments['transaction_date']

                tx_id = client.execute_kw('moneta.transaction', 'create', [tx_vals])
                res = {"success": True, "transaction_id": tx_id, "amount": tx_vals['amount']}

            elif tool_name == "moneta_get_budgets":
                budgets = client.execute_kw('moneta.budget', 'search_read', [[('active', '=', True)]], ['name', 'category_ids'])
                res = {"budgets": budgets}

            elif tool_name == "moneta_get_upcoming_bills":
                days = arguments.get("days", 14)
                today = datetime.now().strftime("%Y-%m-%d")
                future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                domain = [('active', '=', True), ('next_date', '>=', today), ('next_date', '<=', future)]
                bills = client.execute_kw('moneta.recurring.transaction', 'search_read', domain, ['name', 'next_date', 'amount', 'account_id', 'frequency'])
                res = {"upcoming_bills": bills}

            elif tool_name == "moneta_simulate_loan_payoff":
                P = float(arguments.get('principal', 0.0))
                r_annual = float(arguments.get('annual_rate', 0.0)) / 100.0
                term_yrs = int(arguments.get('term_years', 30))
                extra_m = float(arguments.get('extra_monthly', 0.0))
                lump = float(arguments.get('lump_sum', 0.0))
                n = term_yrs * 12
                r = r_annual / 12.0
                pmt = (P * (r * ((1 + r) ** n)) / (((1 + r) ** n) - 1)) if r > 0 else (P / n)
                bal = P
                months = 0
                act_interest = 0.0
                while bal > 0.01 and months < 1200:
                    months += 1
                    interest = bal * r
                    act_interest += interest
                    prin = min(pmt - interest + extra_m + (lump if months == 1 else 0.0), bal)
                    bal -= prin

                res = {
                    "standard_monthly_payment": round(pmt, 2),
                    "accelerated_months": months,
                    "accelerated_years": round(months / 12.0, 1),
                    "months_saved": max(n - months, 0),
                    "years_saved": round(max(n - months, 0) / 12.0, 1),
                    "total_interest_paid": round(act_interest, 2),
                }

            elif tool_name == "moneta_undo_last_action":
                res = client.execute_kw('moneta.action.history', 'action_undo_last', [])

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
                }

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(res, indent=2)}
                    ]
                }
            }

        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(exc)}
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method '{method}' not supported"}
    }


def main():
    parser = argparse.ArgumentParser(description="Moneta Finance MCP Server")
    parser.add_argument("--url", default=os.getenv("ODOO_URL", "http://localhost:8069"))
    parser.add_argument("--db", default=os.getenv("ODOO_DB", "weeseng"))
    parser.add_argument("--user", default=os.getenv("ODOO_USER", "admin"))
    parser.add_argument("--password", default=os.getenv("ODOO_PASSWORD", "admin"))
    args = parser.parse_args()

    client = None
    try:
        client = MonetaClient(args.url, args.db, args.user, args.password)
    except Exception as exc:
        sys.stderr.write(f"Warning: Could not pre-authenticate with Odoo: {exc}\n")

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            resp = handle_request(client, req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error handling message: {e}\n")


if __name__ == "__main__":
    main()
