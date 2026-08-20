# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api, _
from .ai_client import MonetaAIClient


class MonetaAIChat(models.Model):
    _name = 'moneta.ai.chat'
    _description = 'Moneta AI Financial Advisor Chat Session'
    _order = 'write_date desc, id desc'

    name = fields.Char(string='Session Title', default='Wealth Advisory Chat', required=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True)
    message_ids = fields.One2many('moneta.ai.chat.message', 'chat_id', string='Messages')
    pending_question = fields.Text(string='Ask a Question...')

    def action_send_message(self):
        """Send question with complete financial ledger context to AI."""
        self.ensure_one()
        if not self.pending_question:
            return

        user_q = self.pending_question.strip()
        self.pending_question = False

        # 1. Store user message
        self.env['moneta.ai.chat.message'].create({
            'chat_id': self.id,
            'role': 'user',
            'content': user_q,
        })

        # 2. Build Comprehensive Ledger Context
        context_str = self._build_financial_context()

        system_prompt = (
            "You are Moneta AI, a world-class fiduciary financial advisor, wealth planner, and personal finance analyst. "
            "You have direct access to the user's real-time financial ledger data below. "
            "Deliver concise, encouraging, mathematically accurate, and highly actionable advice. "
            "Format your response with clean Markdown bullet points and bold highlights.\n\n"
            f"--- USER FINANCIAL LEDGER CONTEXT ---\n{context_str}\n--------------------------------------"
        )

        # 3. Call AI
        ai_reply = MonetaAIClient.generate_text(self.env, system_prompt, user_q)

        # 4. Store Assistant message
        self.env['moneta.ai.chat.message'].create({
            'chat_id': self.id,
            'role': 'assistant',
            'content': ai_reply,
        })
        return True

    def _build_financial_context(self):
        user = self.env.user
        today = date.today()
        m_start = today.replace(day=1)

        # Accounts & Balances
        accounts = self.env['moneta.account'].search([('user_id', '=', user.id), ('is_closed', '=', False)])
        acc_summary = []
        net_worth = 0.0
        for a in accounts:
            bal = float(a.current_balance or 0.0)
            net_worth += bal
            acc_summary.append(f"- {a.name} ({a.account_type}): ${bal:,.2f}")

        # This Month Cash Flow
        txs = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', m_start),
            ('state', '!=', 'void'),
            ('is_transfer', '=', False),
        ])
        income = sum(float(t.amount) for t in txs if t.amount > 0)
        expenses = abs(sum(float(t.amount) for t in txs if t.amount < 0))
        savings_rate = ((income - expenses) / income * 100.0) if income > 0 else 0.0

        # Goals
        goals = self.env['moneta.goal'].search([('user_id', '=', user.id)])
        goals_summary = [f"- {g.name}: ${g.current_amount:,.2f} of ${g.target_amount:,.2f} ({int(g.progress_percent)}%)" for g in goals]

        # Properties & Equity
        prop_summary = []
        if 'moneta.property' in self.env:
            props = self.env['moneta.property'].search([('user_id', '=', user.id)])
            prop_summary = [f"- {p.name} ({p.asset_category}): Value ${p.current_market_value:,.2f}, Debt ${p.mortgage_balance:,.2f}, Equity ${p.equity_value:,.2f}" for p in props]

        context = (
            f"Date: {today}\n"
            f"Net Worth (Liquid/Accounts): ${net_worth:,.2f}\n"
            f"This Month Income: ${income:,.2f}\n"
            f"This Month Expenses: ${expenses:,.2f}\n"
            f"Net Savings: ${income - expenses:,.2f} (Savings Rate: {savings_rate:.1f}%)\n\n"
            f"Active Accounts:\n" + ("\n".join(acc_summary) if acc_summary else "None") + "\n\n"
            f"Financial Goals:\n" + ("\n".join(goals_summary) if goals_summary else "None") + "\n\n"
            f"Properties & Tangible Assets:\n" + ("\n".join(prop_summary) if prop_summary else "None")
        )
        return context


class MonetaAIChatMessage(models.Model):
    _name = 'moneta.ai.chat.message'
    _description = 'Moneta AI Chat Message'
    _order = 'create_date asc, id asc'

    chat_id = fields.Many2one('moneta.ai.chat', string='Chat Session', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', related='chat_id.user_id', store=True, index=True)
    role = fields.Selection([('user', 'You'), ('assistant', 'Moneta AI')], string='Role', required=True)
    content = fields.Text(string='Message Content', required=True)
    create_date = fields.Datetime(string='Timestamp', readonly=True)
