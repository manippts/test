# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    purchase_type = fields.Selection([('normal','Normal'),('job_order','Job-Order')], string='Purchase Type', copy=False, default='normal', track_visibility='onchange')  
   
    
    @api.model
    def create(self, vals):
        if vals.get('purchase_type') == 'job_order':
            vals['name'] = self.env['ir.sequence'].next_by_code('job.order') or '/'
        return super(PurchaseOrder, self).create(vals)
    

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True, required=False)

    