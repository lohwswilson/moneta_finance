# -*- coding: utf-8 -*-
{
    'name': 'Moneta Finance - Malaysia Wealth & Tax',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Personal Finance',
    'summary': 'Malaysia Personal Finance Hub: EPF/KWSP 3-Account Hub, LHDN Borang BE Tax Relief Planner, PRS, ASNB Unit Trusts (ASB/ASM), Flexi-Home Loans (SBR), and RPGT',
    'author': 'Moneta Finance / Wilson Loh',
    'license': 'LGPL-3',
    'depends': ['moneta_finance', 'moneta_finance_property'],
    'pre_init_hook': '_pre_init_transfer_malaysia_data',
    'data': [
        'security/ir.model.access.csv',
        'security/malaysia_record_rules.xml',
        'data/malaysia_master_data.xml',
        'views/epf_views.xml',
        'views/lhdn_tax_views.xml',
        'views/malaysia_investments_views.xml',
        'views/malaysia_property_loan_views.xml',
        'views/malaysia_menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
