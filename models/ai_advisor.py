# -*- coding: utf-8 -*-
import json
import base64
import urllib.request
import urllib.error
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MonetaAIClient:
    """Universal AI Client supporting Google Gemini and OpenAI REST APIs."""

    @staticmethod
    def get_config(env):
        params = env['ir.config_parameter'].sudo()
        provider = params.get_param('moneta.ai_provider', 'gemini')
        api_key = params.get_param('moneta.ai_api_key', '')
        model = params.get_param('moneta.ai_model', 'gemini-1.5-flash')
        return provider, api_key, model

    @classmethod
    def generate_text(cls, env, system_prompt, user_prompt):
        provider, api_key, model = cls.get_config(env)
        if not api_key:
            return cls._fallback_response(user_prompt)

        try:
            if provider == 'gemini':
                return cls._call_gemini(api_key, model, system_prompt, user_prompt)
            else:
                return cls._call_openai(api_key, model, system_prompt, user_prompt)
        except Exception as e:
            return f"⚠️ AI Error: {str(e)}\n\nPlease verify your API key and network connection in Configuration."

    @classmethod
    def analyze_image(cls, env, image_base64, prompt):
        provider, api_key, model = cls.get_config(env)
        if not api_key:
            return cls._fallback_receipt_data()

        try:
            if provider == 'gemini':
                return cls._call_gemini_vision(api_key, model or 'gemini-1.5-flash', image_base64, prompt)
            else:
                return cls._call_openai_vision(api_key, model or 'gpt-4o-mini', image_base64, prompt)
        except Exception as e:
            raise UserError(_("AI Vision OCR Failed: %s") % str(e))

    @staticmethod
    def _call_gemini(api_key, model, system_prompt, user_prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"System Instructions:\n{system_prompt}\n\nUser Question:\n{user_prompt}"}]}
            ],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['candidates'][0]['content']['parts'][0]['text']

    @staticmethod
    def _call_openai(api_key, model, system_prompt, user_prompt):
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']

    @staticmethod
    def _call_gemini_vision(api_key, model, image_base64, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": image_base64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['candidates'][0]['content']['parts'][0]['text']

    @staticmethod
    def _call_openai_vision(api_key, model, image_base64, prompt):
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']

    @staticmethod
    def _fallback_response(query):
        return (
            "🤖 **Moneta AI Wealth Advisor (Demo Mode)**\n\n"
            "To enable live AI insights powered by **Google Gemini** or **OpenAI**, please configure your API key in **Moneta Settings**.\n\n"
            f"*Your question was:* \"{query}\"\n\n"
            "**Key Financial Principles:**\n"
            "1. **Emergency Buffer**: Ensure you maintain 3–6 months of living expenses in liquid high-yield savings.\n"
            "2. **Debt Optimization**: Prioritize high-interest debt (>7%) before expanding discretionary spending.\n"
            "3. **Budget Discipline**: Target a 50/30/20 allocation (50% Needs, 30% Wants, 20% Savings/Investments)."
        )

    @staticmethod
    def _fallback_receipt_data():
        return json.dumps({
            "merchant": "Sample Store",
            "date": str(date.today()),
            "total_amount": 42.50,
            "tax_amount": 3.50,
            "line_items": [
                {"description": "Item 1", "amount": 25.00, "category_suggestion": "Groceries"},
                {"description": "Item 2", "amount": 14.00, "category_suggestion": "Household"}
            ]
        })


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


class MonetaAISummary(models.Model):
    _name = 'moneta.ai.summary'
    _description = 'Executive Monthly AI Financial Health Summary'
    _order = 'summary_month desc, id desc'

    name = fields.Char(string='Report Title', required=True)
    summary_month = fields.Date(string='Report Month', default=fields.Date.context_today, required=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True)
    executive_narrative = fields.Html(string='AI Executive Narrative Report')

    def action_generate_narrative(self):
        """Generate monthly comprehensive AI executive report."""
        self.ensure_one()
        user = self.env.user
        today = self.summary_month or date.today()
        m_start = today.replace(day=1)
        prev_m = (m_start - relativedelta(months=1))

        # Gather Ledger Statistics
        txs = self.env['moneta.transaction'].search([
            ('user_id', '=', user.id),
            ('transaction_date', '>=', m_start),
            ('transaction_date', '<=', today),
            ('state', '!=', 'void'),
            ('is_transfer', '=', False),
        ])
        income = sum(float(t.amount) for t in txs if t.amount > 0)
        expenses = abs(sum(float(t.amount) for t in txs if t.amount < 0))

        system_prompt = (
            "You are an executive personal CFO generating a formal, beautifully formatted Monthly Financial Health Report in HTML format. "
            "Include sections for: 1. Executive Summary, 2. Cash Flow & Savings Analysis, 3. Category Spending Highlights, 4. Top 3 Actionable Recommendations for Next Month. "
            "Use clean HTML tags like <h3>, <ul>, <li>, <strong>, and badges."
        )
        user_prompt = f"Generate my Monthly Financial Report for {today.strftime('%B %Y')}. Income: ${income:,.2f}, Expenses: ${expenses:,.2f}, Net Savings: ${income - expenses:,.2f}."

        report_html = MonetaAIClient.generate_text(self.env, system_prompt, user_prompt)
        self.executive_narrative = report_html
        return True
