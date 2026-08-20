# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from .ai_client import MonetaAIClient


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
