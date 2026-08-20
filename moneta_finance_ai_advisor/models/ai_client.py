# -*- coding: utf-8 -*-
import json
import base64
import urllib.request
import urllib.error
from datetime import date
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
