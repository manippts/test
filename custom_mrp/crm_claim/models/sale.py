# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_type = fields.Selection([('normal','Normal'),('service','Services')], string="Sale Type", copy=False, track_visibility='onchange', default='normal')
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def _prepare_invoice_line(self, qty):
        result = super(SaleOrderLine, self)._prepare_invoice_line(qty=qty)
        result['sale_line_id']= self.id
        return result