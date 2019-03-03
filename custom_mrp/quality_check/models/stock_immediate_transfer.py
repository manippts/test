# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time
from dateutil.relativedelta import relativedelta
import datetime
import dateutil
from datetime import datetime

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'
    
    @api.multi
    def process(self):
        self.ensure_one()
        # If still in draft => confirm and assign
        if self.pick_id.state == 'draft':
            self.pick_id.action_confirm()
            if self.pick_id.state != 'assigned':
                self.pick_id.action_assign()
                if self.pick_id.state != 'assigned':
                    raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
        for pack in self.pick_id.pack_operation_ids:
            if pack.product_qty > 0:
                pack.write({'qty_done': pack.product_qty})
            else:
                pack.unlink()
                
        if self.pick_id.picking_type_id.code == 'incoming':
            quality_accept_obj = self.env['quality.accept']
            quality_line_content = []
            for in_picking in self.pick_id.pack_operation_ids:
                if in_picking.product_id.qual_check:
                    quality_line_content.append((0,0,{'product_id':in_picking.product_id.id,'product_uom':in_picking.product_uom_id.id,
                    'received_qty':in_picking.qty_done,'accept_location_id':in_picking.location_dest_id.id}))
            if quality_line_content:
                vals = {'date': datetime.now().date(), 'grn_id': self.pick_id.id, 'partner_id': self.pick_id.partner_id and self.pick_id.partner_id.id or False, 'quality_line': quality_line_content}
                quality_id = quality_accept_obj.create(vals)  
                self.pick_id.write({'quality_id': quality_id.id})       
        self.pick_id.do_transfer()
