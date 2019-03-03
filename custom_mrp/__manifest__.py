# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Manufacturing',
    'version': '1.0',
    'category': 'Manufacturing',
    'sequence': 3,
    'description':"Work Order Management",
    'author': 'PPTS',
    'website': 'http://www.pptssolutions.com',
    'depends': ['base', 'mrp', 'stock', 'stock_indent', 'purchase'],
    'data': [
        'wizard/sub_contracting_view.xml',
        'wizard/multiple_material_request.xml',
        'wizard/workcenter_quality_view.xml',
#         'security/hr_inherit_security.xml',
#         'security/ir.model.access.csv',
        'views/mrp_view.xml',
        'views/purchase_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
