# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PurchaseRequisitionDetails(models.TransientModel):
    _name = 'purchase.requisition.details'
    _description = 'Purchase wizard'

    indent_id = fields.Many2one('indent.indent', 'Indent')
    item_ids = fields.One2many('purchase.requisition.details.items', 'transfer_id', 'Items', domain=[('product_id', '!=', False)])
    
    @api.model
    def default_get(self, fields):
#         if context is None: context = {}
        res = super(PurchaseRequisitionDetails, self).default_get(fields)
        indent_ids = self._context.get('active_ids', [])
        active_model = self._context.get('active_model')

        if not indent_ids or len(indent_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('indent.indent'), 'Bad context propagation'
        indent_id = indent_ids
        indent = self.env['indent.indent'].browse(indent_id)
        items = []
        for op in indent.product_lines:
            item = {
                'product_id': op.product_id.id,
                'product_uom': op.product_uom.id,
                'product_uom_qty': op.product_uom_qty,
            }
            items.append((0,0,item))
        res['item_ids']=items
        res['indent_id']=indent.id
        return res

    @api.one
    def do_detailed_transfer(self):
        indent_obj = self.env['indent.indent']
        req_id = indent_obj._create_purchase_req(self.indent_id)
        for line in self.item_ids:
            indent_obj._create_purchase_req_line(self.indent_id, line, req_id)
        self.indent_id.write({'requisition_id': req_id.id})
        return True


class PurchaseRequisitionDetails_items(models.TransientModel):
    _name = 'purchase.requisition.details.items'
    _description = 'Purchase wizard items'

    transfer_id = fields.Many2one('purchase.requisition.details', 'Transfer')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure')
    product_uom_qty = fields.Float('Quantity', default = 1.0)
