# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    mrp_type = fields.Selection([('inhouse', 'In-House'), ('sub_contracting', 'Sub Contracting')], 'Type', default='inhouse')
    out_picking_id = fields.Many2one('stock.picking', 'Delivery', copy=False)
    in_picking_id = fields.Many2one('stock.picking', 'Incoming', copy=False)
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', copy=False)
    material_req_id = fields.Many2many('indent.indent', 'mrp_req_rel', 'mrp_id', 'req_id', 'Material Requisition', copy=False)
    work_order_level = fields.Boolean('Work Order Level', default=False, copy=False)

    
    @api.multi
    def do_produce(self):
        if not self.out_picking_id and not self.purchase_id:
            raise UserError(('Please complete the sub-contracting.'))
        if self.move_finished_ids:
            for rec in self.move_finished_ids:
                rec.write({'sub_contract_done_quantity':rec.product_uom_qty})
        self.write({'state':'done'})
        return True
    
    @api.multi
    def action_view_meterial_request(self):
        material_req_ids = self.mapped('material_req_id')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('stock_indent.action_indent_indent')
        list_view_id = imd.xmlid_to_res_id('stock_indent.view_indent_indent_tree')
        form_view_id = imd.xmlid_to_res_id('stock_indent.view_stock_indent_indent_form')
        if not material_req_ids:
            raise UserError(('Please raise the material request!.'))
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(material_req_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % material_req_ids.ids
        elif len(material_req_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = material_req_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    @api.multi
    def create_material_request(self):
        material_obj = self.env['indent.indent']
        values = {}
        origin = ''
        for record in self:
            if not record.move_raw_ids:
                raise UserError(('Please click on "Confirm Production" to get consumed products.'))
            lines = []
            for move_line in record.move_raw_ids:
                lines.append((0, 0, {'name' : record.name, 'product_id': move_line.product_id.id, 'qty_available': move_line.product_id.qty_available, 'virtual_available': move_line.product_id.virtual_available, 'product_uom_qty': move_line.product_uom_qty, 'product_uom': move_line.product_uom.id, 'price_unit': move_line.product_id.standard_price}))
            values['name'] = '/'
            values['department_id'] = 1
            values['purpose'] = "To Manufacture"
            if record.origin:
                origin = record.origin + ' / '
            values['origin'] = origin + str(record.name)
            values['product_lines'] = lines
            material_req_id = material_obj.create(values)
            record.write({'material_req_id': [(4, material_req_id.id)]})
        return True
    
class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    
    done_qty = fields.Float('Done Qty')
    received_qty = fields.Float('Received Qty')
    produced_qty = fields.Float('Produced Qty')
    quality_line_ids = fields.One2many('workcenter.quality.line', 'workcenter_id', 'Quality Lines')
    work_center_type = fields.Selection([('inhouse', 'In-House'), ('sub_contracting', 'Sub Contracting')], 'Type', default='inhouse')
    is_work_order_level = fields.Boolean(string='Work Order Level', related='production_id.work_order_level', readonly=True)
    mr_pro__id = fields.Many2one('indent.indent', 'Material Request', readonly=True)
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', copy=False, readonly=True)
    out_picking_id = fields.Many2one('stock.picking', 'Delivery', copy=False, readonly=True)
    in_picking_id = fields.Many2one('stock.picking', 'Incoming', copy=False, readonly=True)
    reference = fields.Char("Reference")

    
    @api.multi
    def record_production(self):
        self.ensure_one()
        if self.work_center_type == 'sub_contracting' and (not self.out_picking_id or self.out_picking_id.state != 'done') and (not self.purchase_id or self.purchase_id.state != 'purchase'):
            raise UserError(('Execute the Sub Contracting Process to make this Work Order Completed.'))
        return super(MrpWorkorder, self).record_production()

    @api.multi
    def create_material_request_from_workcenter(self):
        material_obj = self.env['indent.indent']
        stock_location_search = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        values = {}
        for record in self:
            if record.mr_pro__id:
                raise UserError(('Material Requisition already created.'))
            lines = []
            for move_raw in record.move_raw_ids:
                lines.append((0, 0, {'name' : record.production_id.name, 'product_id': move_raw.product_id.id, 'product_uom_qty': move_raw.product_uom_qty, 'product_uom': move_raw.product_uom.id, 'price_unit': move_raw.product_id.standard_price}))
            values['name'] = '/'
            values['department_id'] = 1
            values['purpose'] = "To Manufacture"
            values['origin'] = record.production_id.name
            values['location_id'] = stock_location_search.id
            values['product_lines'] = lines
            material_req_id = material_obj.create(values)
            record.write({'mr_pro__id': material_req_id.id})
        return True
    
    @api.multi
    def action_view_meterial(self):
        imd = self.env['ir.model.data']
        material_obj = self.env['indent.indent']
        action = imd.xmlid_to_object('stock_indent.action_indent_indent')
        list_view_id = imd.xmlid_to_res_id('stock_indent.view_indent_indent_tree')
        form_view_id = imd.xmlid_to_res_id('stock_indent.view_stock_indent_indent_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        meterial_request_ids = material_obj.search([('id', '=', self.mr_pro__id.id)])
        if len(meterial_request_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % meterial_request_ids.ids
        elif len(meterial_request_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = meterial_request_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    
    @api.model
    def create(self, vals):
        vals['reference'] =  self.env['ir.sequence'].get('mrp.seq') or '/'
        return super(MrpWorkorder, self).create(vals)
    
    @api.multi
    def action_record_production_quality(self):
        self.ensure_one()
        if self.is_work_order_level and self.work_center_type == 'sub_contracting':
            self.record_production()
        else:
            ctx = dict()
            ctx.update({
                'default_produce_qty': self.qty_production,
                'default_product_id': self.product_id.id,
                 })
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
                        'res_id': False,
                        'context': ctx,
                    }

class WorkcenterQualityLine(models.Model):
    _name = 'workcenter.quality.line'

    date_time = fields.Datetime('Date and Time')
    produced_qty = fields.Float('Produced Qty')
    accepted_qty = fields.Float('Accepted Qty')
    rejected_qty = fields.Float('Rejected Qty')
    rework_qty = fields.Float('Rework Qty')
    workcenter_id = fields.Many2one('mrp.workorder', 'Work Order')


class MrpWorkCenter(models.Model):
    _inherit = "mrp.workcenter"

    location_id = fields.Many2one('stock.location', 'Work Center Location')
    