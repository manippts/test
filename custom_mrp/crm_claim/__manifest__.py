# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Crm Claim',
    'version' : '1.1',
    'summary': 'Crm Claim',
    'sequence': 1,
    'description': """ """,
    'category': 'Crm Claim',
    'author': 'PPTS [India] Pvt.Ltd.',
    'website': 'https://www.pptssolutions.com',
    'images' : [],
    'depends' : ['base', 'crm', 'sale', 'sales_team', 'stock', 'account', 'mail','stock_indent'],
    'data': ['views/crm_claim_view.xml',
              'views/crm_claim_configuration_view.xml', 
              'views/sales_view.xml',
              'views/account_invoice_view.xml'],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
