# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Calibration',
    'version' : '1.1',
    'summary': 'Calibration',
    'sequence': 30,
    'description': """ """,
    'category': 'General',
    'author': 'PPTS [India] Pvt.Ltd.',
    'website': 'https://www.pptssolutions.com',
    'images' : [],
    'depends' : ['base_setup', 'crm', 'sale', 'account_asset'],
    'data': [
            'views/calibration.xml',
            'views/cus_asset.xml',
            ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
