# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import math
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class WorkcenterQualityWizard(models.TransientModel):
    _name = 'workcenter.quality.wizard'
    
    
    product_id = fields.Many2one('product.product', 'Product')
    produced_qty = fields.Float('Produced Qty')
    produce_qty = fields.Float('Quantity to Produce', default=1.0)
    quality_check = fields.Boolean('Quality Check', default=False)
    product_tracking = fields.Selection('Product Tracking', related='product_id.tracking', help='Technical: used in views only.')
    accepted_qty = fields.Float('Accepted Qty')
    rejected_qty = fields.Float('Rejected Qty')
    rework_qty = fields.Float('Rework Qty')
    rework = fields.Text('Reason For Rework ')
    rejection = fields.Text('Reason For Rejection')
    wiz_lot_id = fields.Many2one('stock.production.lot', 'Lot', domain="[('product_id', '=', product_id)]")

    @api.multi
    def enable_quality(self):
        workcenter_obj = self.env['mrp.workorder']
        stock_move_obj = self.env['stock.move']
        order_br = workcenter_obj.browse(self.env.context['active_id'])

        if self.product_tracking == 'serial' and not self.produced_qty == 1:
            raise UserError(('Can produce only one product at a time. As Product is tracked by unique Serial Number.'))

        if self.produced_qty > (order_br.qty_production - order_br.qty_produced):
            raise UserError(('Cannot produce more than ' + str(order_br.qty_production)))

        self.write({'quality_check': True})
        view = self.env.ref('custom_mrp.view_workcenter_quality_wizard_form')
        return {
                    'name': ('Workcenter Quality'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'workcenter.quality.wizard',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': self.id,
                    'context': self.env.context,
                }
        return True
    
    @api.multi
    def get_successor_workorder(self, workorder_id):
        workorder_obj = self.env['mrp.workorder']
        workorder_search = workorder_obj.search([('next_work_order_id', '=', workorder_id)])
        return workorder_search
    
    @api.multi
    def action_confirm(self):
        workorder_obj = self.env['mrp.workorder']
        stock_move_obj = self.env['stock.move']
        mrp_production_obj = self.env['mrp.production']
        order_br = workorder_obj.browse(self.env.context['active_id'])
        
        if self.product_tracking == 'serial' and not (self.accepted_qty == 1 or self.rejected_qty == 1 or self.rework_qty == 1):
            raise UserError(('Can produce only one product at a time.As Product is tracked by unique Serial Number.'))

        if self.produced_qty > (order_br.qty_production - order_br.qty_produced):
            raise UserError(('Cannot produce more than ' + str(order_br.qty_production)))
        
        if not self.accepted_qty and not self.rejected_qty and not self.rework_qty: 
            raise UserError(('Please update the Accepted, Rejected or Rework Quantities.'))

        
        done_qty = self.accepted_qty + self.rejected_qty + order_br.done_qty
        

        quality_vals = [(0, 0, {
                'date_time': fields.Datetime.now(),
                'produced_qty': self.produced_qty,
                'accepted_qty': self.accepted_qty,
                'rejected_qty': self.rejected_qty,
                'rework_qty': self.rework_qty,
        })]
        if self.accepted_qty:
            order_br.write({'qty_producing': self.accepted_qty, 'final_lot_id': self.wiz_lot_id.id, 'done_qty': done_qty, 'quality_line_ids': quality_vals})
            order_br.record_production()
            order_br.next_work_order_id.write({'received_qty': self.accepted_qty})
            order_br.next_work_order_id.button_start()
        else:
            order_br.write({'quality_line_ids': quality_vals})
        return True
