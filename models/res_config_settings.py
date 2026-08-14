# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Main Base Currency',
        readonly=False,
        help='Main base reporting currency for your accounts and reports.'
    )
    group_multi_currency = fields.Boolean(
        string='Multi-Currencies',
        implied_group='base.group_multi_currency',
        help='Allows multi-currency bank accounts, transfers, and foreign currency exchange rates.'
    )

    moneta_ai_provider = fields.Selection([
        ('gemini', 'Google Gemini (Recommended)'),
        ('openai', 'OpenAI (GPT-4o / GPT-4o-mini)'),
    ], string='AI Provider', default='gemini', config_parameter='moneta.ai_provider')

    moneta_ai_api_key = fields.Char(
        string='AI API Key', config_parameter='moneta.ai_api_key',
        help='Google Gemini or OpenAI API Key for AI Financial Advisor, Receipt OCR, and Transaction Enrichment.',
    )

    moneta_ai_model = fields.Char(
        string='Model Name', default='gemini-1.5-flash', config_parameter='moneta.ai_model',
        help='e.g. gemini-1.5-flash, gemini-1.5-pro, gpt-4o-mini, gpt-4o',
    )
