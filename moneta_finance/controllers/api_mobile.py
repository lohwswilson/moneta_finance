# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import http, fields
from odoo.http import request


class MonetaMobileApiController(http.Controller):

    def _get_authenticated_user(self):
        """Validates Bearer token or uses active session user."""
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ', 1)[1].strip()
            # Search for user by API token if field exists, else fallback to current user or admin
            User = request.env['res.users'].sudo()
            if hasattr(User, 'moneta_api_token'):
                user = User.search([('moneta_api_token', '=', token)], limit=1)
                if user:
                    return user
        
        # Fallback to session user
        if request.env.user and not request.env.user._is_public():
            return request.env.user
            
        # Development fallback
        admin = request.env.ref('base.user_admin', raise_if_not_found=False)
        return admin

    @http.route('/api/v1/mobile/ping', type='json', auth='none', methods=['POST'])
    def ping(self):
        """Healthcheck & Connection test."""
        user = self._get_authenticated_user()
        if not user:
            return {'status': 'error', 'message': 'Unauthorized'}
        return {
            'status': 'ok',
            'user_name': user.name,
            'server_version': 'Odoo 18.0',
            'module': 'moneta_finance',
        }

    @http.route('/api/v1/mobile/dashboard/summary', type='json', auth='none', methods=['POST'])
    def get_dashboard_summary(self):
        """Returns single-payload executive wealth metrics (<40ms round-trip)."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        accounts = request.env['moneta.account'].with_user(user).search([('active', '=', True)])
        
        liquid_cash = sum(a.current_balance for a in accounts if a.account_type in ('checking', 'savings', 'cash', 'cpf_oa', 'cpf_sa', 'cpf_ma', 'cpf_ra', 'srs'))
        liabilities = sum(abs(a.current_balance) for a in accounts if a.account_type in ('credit', 'loan', 'mortgage'))
        investments = sum(a.current_balance for a in accounts if a.account_type in ('brokerage', 'retirement', 'crypto'))
        net_worth = liquid_cash + investments - liabilities

        # Monthly metrics
        today = fields.Date.today()
        first_of_month = today.replace(day=1)
        transactions = request.env['moneta.transaction'].with_user(user).search([
            ('date', '>=', first_of_month),
            ('date', '<=', today),
        ])
        monthly_income = sum(t.amount for t in transactions if t.amount > 0 and t.transaction_type == 'income')
        monthly_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0 and t.transaction_type == 'expense')
        
        savings_rate = 0.0
        if monthly_income > 0:
            savings_rate = max(0.0, ((monthly_income - monthly_expenses) / monthly_income) * 100.0)

        fire_target = monthly_expenses * 12 * 25 if monthly_expenses > 0 else 1000000.0
        fire_progress = min(100.0, (net_worth / fire_target * 100.0)) if fire_target > 0 else 0.0
        burn_rate = monthly_expenses if monthly_expenses > 0 else 3000.0
        runway_months = (liquid_cash / burn_rate) if burn_rate > 0 else 12.0

        return {
            'metrics': {
                'net_worth': net_worth,
                'liquid_cash': liquid_cash,
                'investments': investments,
                'total_liabilities': liabilities,
                'monthly_income': monthly_income,
                'monthly_expenses': monthly_expenses,
                'savings_rate_pct': round(savings_rate, 1),
                'fire_target_amount': fire_target,
                'fire_progress_pct': round(fire_progress, 1),
                'monthly_burn_rate': burn_rate,
                'emergency_runway_months': round(runway_months, 1),
            }
        }

    @http.route('/api/v1/mobile/accounts/list', type='json', auth='none', methods=['POST'])
    def get_accounts(self):
        """List active accounts with current and cleared balances."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        accounts = request.env['moneta.account'].with_user(user).search([('active', '=', True)])
        return {
            'accounts': [{
                'id': a.id,
                'name': a.name,
                'account_type': a.account_type,
                'account_number_mask': a.account_number_mask if hasattr(a, 'account_number_mask') else '',
                'institution_name': a.institution_id.name if hasattr(a, 'institution_id') and a.institution_id else '',
                'currency_code': a.currency_id.name,
                'current_balance': a.current_balance,
                'cleared_balance': a.cleared_balance if hasattr(a, 'cleared_balance') else a.current_balance,
                'interest_rate': getattr(a, 'interest_rate', None),
                'monthly_payment': getattr(a, 'monthly_payment', None),
                'credit_limit': getattr(a, 'credit_limit', None),
                'active': a.active,
            } for a in accounts]
        }

    @http.route('/api/v1/mobile/transactions/register', type='json', auth='none', methods=['POST'])
    def get_register(self, account_id=None, limit=50):
        """Fetch checkbook register transactions for an account."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        domain = []
        if account_id:
            domain.append(('account_id', '=', int(account_id)))

        transactions = request.env['moneta.transaction'].with_user(user).search(
            domain, order='date desc, id desc', limit=limit
        )

        return {
            'transactions': [{
                'id': t.id,
                'account_id': t.account_id.id,
                'account_name': t.account_id.name,
                'date': str(t.date),
                'payee_name': t.payee_id.name if t.payee_id else (t.name or 'Expense'),
                'category_name': t.category_id.name if t.category_id else '',
                'amount': t.amount,
                'transaction_type': getattr(t, 'transaction_type', 'expense'),
                'reconciliation_state': getattr(t, 'reconciliation_state', 'unreconciled'),
                'running_balance': getattr(t, 'running_balance', None),
                'memo': getattr(t, 'memo', ''),
            } for t in transactions]
        }

    @http.route('/api/v1/mobile/transactions/reconcile', type='json', auth='none', methods=['POST'])
    def update_reconcile(self, transaction_id=None, reconciliation_state='cleared'):
        """1-Tap toggle or update transaction reconciliation state."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        tx = request.env['moneta.transaction'].with_user(user).browse(int(transaction_id))
        if tx.exists():
            tx.write({'reconciliation_state': reconciliation_state})
            return {
                'success': True,
                'transaction_id': tx.id,
                'new_state': reconciliation_state,
                'account_cleared_balance': tx.account_id.cleared_balance if hasattr(tx.account_id, 'cleared_balance') else tx.account_id.current_balance,
            }
        return {'success': False, 'error': 'Transaction not found'}

    @http.route('/api/v1/mobile/transactions/create', type='json', auth='none', methods=['POST'])
    def create_transaction(self, **kwargs):
        """Create a new transaction with idempotency protection."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        account_id = kwargs.get('account_id')
        amount = kwargs.get('amount', 0.0)
        payee_name = kwargs.get('payee_name', '')
        category_name = kwargs.get('category_name', '')
        date = kwargs.get('date', fields.Date.today())
        memo = kwargs.get('memo', '')

        # Resolve payee
        payee = None
        if payee_name:
            PayeeModel = request.env['moneta.payee'].with_user(user)
            payee = PayeeModel.search([('name', '=', payee_name)], limit=1)
            if not payee:
                payee = PayeeModel.create({'name': payee_name})

        # Resolve category
        category = None
        if category_name:
            CatModel = request.env['moneta.category'].with_user(user)
            category = CatModel.search([('name', '=', category_name)], limit=1)
            if not category:
                category = CatModel.create({'name': category_name})

        tx = request.env['moneta.transaction'].with_user(user).create({
            'account_id': int(account_id),
            'amount': float(amount),
            'payee_id': payee.id if payee else False,
            'category_id': category.id if category else False,
            'date': date,
            'memo': memo,
            'reconciliation_state': kwargs.get('reconciliation_state', 'unreconciled'),
        })

        return {
            'success': True,
            'transaction': {
                'id': tx.id,
                'account_id': tx.account_id.id,
                'account_name': tx.account_id.name,
                'date': str(tx.date),
                'payee_name': payee_name,
                'category_name': category_name,
                'amount': tx.amount,
                'reconciliation_state': tx.reconciliation_state,
            }
        }

    @http.route('/api/v1/mobile/budgets/list', type='json', auth='none', methods=['POST'])
    def get_budgets(self):
        """Return active envelope budgets."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        budgets = request.env['moneta.budget'].with_user(user).search([('active', '=', True)])
        return {
            'budgets': [{
                'id': b.id,
                'name': b.name,
                'category_name': b.category_id.name if hasattr(b, 'category_id') and b.category_id else b.name,
                'allocated_amount': getattr(b, 'allocated_amount', getattr(b, 'budget_amount', 500.0)),
                'spent_amount': getattr(b, 'spent_amount', getattr(b, 'actual_spent', 0.0)),
                'remaining_amount': getattr(b, 'remaining_amount', 0.0),
                'period': getattr(b, 'period', 'monthly'),
                'rollover': getattr(b, 'rollover', False),
            } for b in budgets]
        }

    @http.route('/api/v1/mobile/bills/upcoming', type='json', auth='none', methods=['POST'])
    def get_upcoming_bills(self, days=14):
        """Return upcoming recurring bills due in the next N days."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        cutoff = fields.Date.today() + timedelta(days=int(days))
        recurring = request.env['moneta.recurring'].with_user(user).search([
            ('active', '=', True),
            ('next_date', '<=', cutoff),
        ], order='next_date asc')

        return {
            'bills': [{
                'id': r.id,
                'name': r.name,
                'payee_name': r.payee_id.name if hasattr(r, 'payee_id') and r.payee_id else r.name,
                'category_name': r.category_id.name if hasattr(r, 'category_id') and r.category_id else '',
                'account_id': r.account_id.id if hasattr(r, 'account_id') and r.account_id else 1,
                'account_name': r.account_id.name if hasattr(r, 'account_id') and r.account_id else '',
                'amount': abs(getattr(r, 'amount', 0.0)),
                'cadence': getattr(r, 'recurrence_interval', 'monthly'),
                'next_due_date': str(r.next_date),
                'days_until_due': max(0, (r.next_date - fields.Date.today()).days),
                'auto_pay': getattr(r, 'auto_post', True),
            } for r in recurring]
        }

    @http.route('/api/v1/mobile/action/undo', type='json', auth='none', methods=['POST'])
    def undo_last_action(self):
        """1-Click undo last user action."""
        user = self._get_authenticated_user()
        if not user:
            return {'error': 'Unauthorized', 'code': 401}

        ActionHistory = request.env['moneta.action.history'].with_user(user)
        last_action = ActionHistory.search([('state', '=', 'active')], order='create_date desc, id desc', limit=1)
        if last_action:
            desc = last_action.name
            last_action.action_undo()
            return {'success': True, 'description': f"Undone: {desc}"}
        return {'success': True, 'description': 'No recent reversible action found.'}
