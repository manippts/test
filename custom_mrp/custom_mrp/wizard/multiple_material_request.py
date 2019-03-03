# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import math
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class MultiMaterialRequest(models.TransientModel):
    _name="multi.material.request"

    product_ids = fields.One2many('material.requisition.items', 'material_req_id', 'Items', domain=[('product_id', '!=', False)])

    @api.model
    def default_get(self, fields):
        res = super(MultiMaterialRequest, self).default_get(fields)
        rec_id = self._context['active_id']
        if rec_id:
            stock_obj = self.env['mrp.production'].browse(rec_id)
            items = []
            for op in stock_obj.move_raw_ids:
                item = {
                    'product_id': op.product_id.id,
                    'product_uom_id': op.product_uom.id,
                    'product_qty': op.product_qty,
                    'scheduled_id': op.id,
                }
                items.append((0,0,item))
            res['product_ids'] = items
        return res

    @api.multi
    def create_material_request_call(self):
        rec_id = self._context['active_id']
        mrp_obj = self.env['mrp.production'].browse(rec_id)
        if rec_id:
            mrp_obj.browse(rec_id).create_material_request()
        return True

class MaterialRequisitionItems(models.TransientModel):
    _name = 'material.requisition.items'

    material_req_id = fields.Many2one('multi.material.request', 'Material Request')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure')
    product_qty = fields.Float('Quantity', default = 1.0)
    scheduled_id = fields.Many2one('mrp.production.product.line', 'Scheduled Product')
