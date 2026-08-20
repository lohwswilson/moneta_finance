# -*- coding: utf-8 -*-
{
    'name': 'Moneta Finance - Real Estate & Property Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Personal Finance',
    'summary': 'Real Estate, Mortgage Linkage, Tenant Leases, Monthly Rent Roll Schedule, and Landlord Analytics',
    'author': 'Moneta Finance / Wilson Loh',
    'license': 'LGPL-3',
    'depends': ['moneta_finance'],
    'data': [
        'security/ir.model.access.csv',
        'security/property_record_rules.xml',
        'views/property_views.xml',
        'views/property_menu_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
