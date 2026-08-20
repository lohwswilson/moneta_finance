# -*- coding: utf-8 -*-
{
    'name': 'Moneta Finance - AI Wealth Advisor & Vision OCR',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Personal Finance',
    'summary': 'AI Personal Wealth Copilot: Interactive Financial Advisor Chat, Executive Monthly Reports, Receipt & Invoice Vision OCR, and Transaction Enrichment',
    'description': """
Moneta AI Wealth Advisor & Vision OCR for Odoo 18
=================================================
An intelligent generative AI extension for Moneta Personal Finance.

Key Features:
-------------
* **Ask Moneta AI Wealth Advisor**:
  - Interactive chat session with live real-time financial ledger context injection.
  - Multi-provider support: Google Gemini (1.5 Flash/Pro) and OpenAI (GPT-4o / GPT-4o-mini).
  - Mathematical accuracy, actionable budgeting tips, and savings rate optimization.

* **Executive Monthly AI Reports**:
  - 1-Click executive personal CFO narrative generator in rich HTML format.
  - Monthly cash flow review, savings highlights, and next month actionable targets.

* **AI Receipt & Invoice Vision OCR**:
  - Multi-modal vision analysis of uploaded receipts and invoice images/PDFs.
  - Automatic itemized split lines extraction, merchant resolution, tax balancing, and attachment linking.

* **Transaction AI Enrichment**:
  - 1-Click clean merchant descriptor normalization and category auto-assignment.
    """,
    'author': 'Moneta Finance / Wilson Loh',
    'website': 'https://github.com/lohwswilson/moneta_finance',
    'license': 'LGPL-3',
    'depends': ['moneta_finance'],
    'data': [
        'security/ir.model.access.csv',
        'security/ai_record_rules.xml',
        'views/ai_advisor_views.xml',
        'views/ai_receipt_views.xml',
        'views/ai_settings_views.xml',
        'views/transaction_views.xml',
        'views/ai_menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
