# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class SubContract(models.Model):
    _name = 'sub.contract'

    partner_id = fields.Many2one('res.partner', 'Supplier', domain=[('supplier', '=', True)])
    
    @api.multi
    def get_picking_type(self, code, company_id):
        picking_type_obj = self.env['stock.picking.type']
        
        picking_type = picking_type_obj.search([('code', '=', code), ('warehouse_id.company_id', '=', company_id)])
        if not picking_type:
            picking_type = picking_type_obj.search([('code', '=', code), ('warehouse_id', '=', False)])
            if not picking_type:
                raise UserError(_('Make sure you have at least an incoming picking type defined'))
        return picking_type

    #Creating Income receipt and Delivery for corresponding (MO)
    @api.multi
    def action_sub_contract(self):
        stock_pick_obj = self.env['stock.picking']
        purchase_obj = self.env['purchase.order']

        model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        if model == 'mrp.production':
            mrp_obj = self.env['mrp.production']
            mrp_br = mrp_obj.browse(res_id)
        
            if not mrp_br.move_raw_ids:
                raise UserError(_("Please click 'Confirm Production' to get consumed product."))
            if mrp_br.purchase_id and mrp_br.out_picking_id:
                raise UserError(_("you have already created the sub-contracting."))
            company_id = self.env.user.company_id.id

            incoming_picking_type_id = self.get_picking_type('incoming', company_id)[0]
            delivery_picking_type_id = self.get_picking_type('outgoing', company_id)[0]
            
            for mris in mrp_br.move_raw_ids:
                mris.write({'sub_contract_done_quantity':mris.product_uom_qty})
                
            out_values = {
                    'partner_id': self.partner_id.id,
                    'picking_type_id': delivery_picking_type_id.id,
                    'origin':mrp_br.name,
                    'location_id':mrp_br.product_id.property_stock_production.id,
                    'location_dest_id':delivery_picking_type_id.default_location_dest_id.id,
                    'move_lines': [],
                }
            lines = []
            for move in mrp_br.move_raw_ids:
                    lines.append((0, 0, {'name': move.product_id.name, 'product_id':move.product_id.id, 'product_uom_qty':move.product_uom_qty, 'product_uom':move.product_uom.id, 'location_id':mrp_br.product_id.property_stock_production.id, 'location_dest_id':delivery_picking_type_id.default_location_dest_id.id }))
            out_values['move_lines'] = lines
            out_picking_id = stock_pick_obj.create(out_values)
            in_values = {
                'origin': mrp_br.name,
                'date_order': fields.Datetime.now(),
                'partner_id': self.partner_id.id,
    #             'pricelist_id': self.partner_id.property_product_pricelist_purchase.id,
                'purchase_type': "job_order",
                'currency_id': self.partner_id.property_purchase_currency_id.id or mrp_br.company_id.currency_id.id,
                'location_id': incoming_picking_type_id.default_location_dest_id.id,
                'company_id': self.env.user.company_id.id,
                'fiscal_position': False,
                'notes': '',
                'emp_id': 1,
                'picking_type_id': incoming_picking_type_id.id,
                'order_line': [(0, 0, {'name': mrp_br.product_id.name, 'product_id': mrp_br.product_id.id, 'product_qty': mrp_br.product_qty, 'product_uom': mrp_br.product_uom_id.id, 'date_planned': fields.datetime.now(), 'price_unit': mrp_br.product_id.standard_price})],
            }
            purchase_id = purchase_obj.create(in_values)
            mrp_br.write({'out_picking_id': out_picking_id.id, 'purchase_id': purchase_id.id})
            if mrp_br.state == 'confirmed':
                mrp_br.write({'state':'progress'})

        elif model == 'mrp.workorder':
            wo_obj = self.env['mrp.workorder']
            wo_br = wo_obj.browse(res_id)

            if wo_br.active_move_lot_ids and wo_br.active_move_lot_ids.filtered(lambda s: s.product_id != 'none' and not s.lot_id):
                raise UserError(_("Please assign Lot Number for Component products."))
            if wo_br.purchase_id and wo_br.out_picking_id:
                raise UserError(_("You have already created the Sub-Contracting."))

            company_id = self.env.user.company_id.id

            incoming_picking_type_id = self.get_picking_type('incoming', company_id)[0]
            delivery_picking_type_id = self.get_picking_type('outgoing', company_id)[0]
            
            delivery_location = delivery_picking_type_id.default_location_dest_id and delivery_picking_type_id.default_location_dest_id.id or self.partner_id.property_stock_customer.id

            out_values = {
                    'partner_id': self.partner_id.id,
                    'picking_type_id': delivery_picking_type_id.id,
                    'origin':wo_br.name,
                    'location_id':wo_br.product_id.property_stock_production.id,
                    'location_dest_id': delivery_location,
                    'move_lines': [],
                }
            lines = []
            for move in wo_br.active_move_lot_ids:
                lines.append((0, 0, {'name': move.product_id.name, 'product_id':move.product_id.id, 'product_uom_qty':move.quantity, 'product_uom':move.product_id.uom_id.id, 'location_id':wo_br.product_id.property_stock_production.id, 'location_dest_id': delivery_location}))
            if not wo_br.active_move_lot_ids:
                lines.append((0, 0, {'name': wo_br.product_id.name, 'product_id':wo_br.product_id.id, 'product_uom_qty':wo_br.qty_production, 'product_uom':wo_br.product_uom_id.id, 'location_id':wo_br.product_id.property_stock_production.id, 'location_dest_id': delivery_location}))
            out_values['move_lines'] = lines
            out_picking_id = stock_pick_obj.create(out_values)
            out_picking_id.action_confirm()
            
            in_values = {
                'origin': wo_br.name,
                'date_order': fields.Datetime.now(),
                'partner_id': self.partner_id.id,
                'purchase_type': "job_order",
                'currency_id': self.partner_id.property_purchase_currency_id.id or wo_br.production_id.company_id.currency_id.id,
                # 'location_id': incoming_picking_type_id.default_location_dest_id.id,
                'company_id': self.env.user.company_id.id,
                'fiscal_position': False,
                'notes': '',
                'emp_id': 1,
                'picking_type_id': incoming_picking_type_id.id,
                'order_line': [(0, 0, {'name': wo_br.product_id.name, 'product_id': wo_br.product_id.id, 'product_qty': wo_br.qty_produced, 'product_uom': wo_br.product_uom_id.id, 'date_planned': fields.datetime.now(), 'price_unit': wo_br.product_id.standard_price})],
            }
            purchase_id = purchase_obj.create(in_values)
            wo_br.write({'out_picking_id': out_picking_id.id, 'purchase_id': purchase_id.id})
            wo_br.button_start()
        return True

