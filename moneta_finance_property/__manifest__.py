# -*- coding: utf-8 -*-
{
    'name': 'Moneta Finance - Rental Property & Tenant Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Personal Finance',
    'summary': 'Landlord Hub: Tenant Leases, Monthly Rent Roll Schedule, Security Deposits, Net Operating Income (NOI), and Rental Yields',
    'author': 'Moneta Finance / Wilson Loh',
    'license': 'LGPL-3',
    'depends': ['moneta_finance'],
    'data': [
        'security/ir.model.access.csv',
        'security/property_record_rules.xml',
        'views/property_views.xml',
        'views/property_menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
