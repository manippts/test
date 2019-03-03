from datetime import datetime
from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp
from collections import Counter


class QualityAccepted(models.Model):
    _name = "quality.accept"
    _description = "Quality Accept"
    _order = 'id desc'
    
    name = fields.Char('Reference No :', size=68, required=True, readonly=True, default='/', copy=False)
    partner_id = fields.Many2one('res.partner', 'Supplier', readonly=True)
    grn_id = fields.Many2one('stock.picking', 'GRN No', readonly=True)
    grn_date = fields.Datetime('GRN Date', related='grn_id.date_done', store=True)
    date = fields.Date('Date', readonly=True)
    accept_date = fields.Date('Accepted Date', readonly=True)
    mrp = fields.Boolean('MRP')
    mrp_no = fields.Char('MRP No', readonly=True, size=30)
    quality_line = fields.One2many('quality.accept.line', 'quality_id', 'Quality Assurance Line')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('quality.accept'))
    state = fields.Selection(
            [('draft', 'New'), ('confirmed', 'Done')],
            string='Status', readonly=True,
            track_visibility='onchange', default='draft')
    show_confirm = fields.Boolean('Check Confirm')
    quality_picking_line = fields.One2many('stock.picking', 'quality_id', 'Quality Pickings', readonly=True)
    
    @api.multi
    def done(self, vals):
        stock_move = self.env['stock.move']
        for quality in self.quality_line:
            if quality.accept_location_dest_id:
                move_date = {
                        'name': self.name,
                        'product_id': quality.product_id.id,
                        'product_uom_qty': quality.received_qty,
                        'product_uom': quality.product_uom.id,
                        'location_id': quality.accept_location_id.id,
                        'location_dest_id': quality.accept_location_dest_id.id,
                        'origin': self.grn_id.origin,
                        'picking_id': self.grn_id.id,
                        'date_expected': self.date,
                        'picking_type_id': self.grn_id.picking_type_id.id,
                        'state': 'draft',
                         }
                new_move = stock_move.create(move_date)
                new_move.action_done()
                
            if quality.rework_location_dest_id:
                    move_date = {
                        'name': self.name,
                        'product_id': quality.product_id.id,
                        'product_uom_qty': quality.received_qty,
                        'product_uom': quality.product_uom.id,
                        'location_id': quality.accept_location_id.id,
                        'location_dest_id': quality.rework_location_dest_id.id,
                        'origin': self.grn_id.origin,
                        'picking_id': self.grn_id.id,
                        'date_expected': self.date,
                        'picking_type_id': self.grn_id.picking_type_id.id,
                        'state': 'draft',
                        }
                         
                    new_move = stock_move.create(move_date)
                    new_move.action_done()
                    
            if quality.reject_location_dest_id:
                    move_date = {
                        'name': self.name,
                        'product_id': quality.product_id.id,
                        'product_uom_qty': quality.received_qty,
                        'product_uom': quality.product_uom.id,
                        'location_id': quality.accept_location_id.id,
                        'location_dest_id': quality.reject_location_dest_id.id,
                        'origin': self.grn_id.origin,
                        'picking_id': self.grn_id.id,
                        'date_expected': self.date,
                        'picking_type_id': self.grn_id.picking_type_id.id,
                        'state': 'draft',
                         }
            
                    new_move = stock_move.create(move_date)
                    new_move.action_done()
             
        for record in self.quality_line:
            if record.state != 'confirmed':
                raise UserError(_('Please confirm your quality lines.'))
            else:
                self.write({'state':'confirmed', 'accept_date': datetime.now().date()})
        return True
    

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] =  self.env['ir.sequence'].get('quality.accept') or '/'
        return super(QualityAccepted, self).create(vals)
    
    @api.multi 
    def write(self, vals):
        for check in self:
            if 'accept_date' not in vals.keys():
                vals['accept_date'] = str(datetime.now().date())
        if 'show_confirm' not in vals.keys():    
            vals['show_confirm'] = True
        return super(QualityAccepted, self).write(vals)  
    
    @api.multi
    def stock_check(self):
        self.env['stock.location']._parent_store_compute()


class QualityAcceptLine(models.Model):
    _name = "quality.accept.line"
    
    state = fields.Selection(
            [('draft', 'New'), ('confirmed', 'Done')],
            string='Status', readonly=True,
            track_visibility='onchange', default='draft')
    product_id = fields.Many2one('product.product', 'Product', required=True,
                help="Sale projection is done for this particular product with corresponding to the cutomer", readonly=True)
    name = fields.Char('Name', size=64, readonly=True)
    product_uom = fields.Many2one('product.uom', 'Product UOM', readonly=True) 
    received_qty = fields.Float('Received Qty', digits=(16, 3), readonly=True)
    accepted_qty = fields.Float('Accepted Qty', digits=(16, 3))
    rejected_qty = fields.Float('Rejected Qty', digits=(16, 3))
    rework_qty = fields.Float('Rework Qty', digits=(16, 3))
    accept_location_id = fields.Many2one('stock.location', 'Accepted Source Location', required=True)
    accept_location_dest_id = fields.Many2one('stock.location', 'Accepted Destination Location')
    rework_location_dest_id = fields.Many2one('stock.location', 'Rework Destination Location')
    reject_location_dest_id = fields.Many2one('stock.location', 'Rejected Destination Location')
    rejected_reason = fields.Text('Rejected Reason')
    rework_reason = fields.Text('Rework Reason')
    quality_id = fields.Many2one('quality.accept', 'Quality Assurance') 
    rejected_deliver_id = fields.Many2one('stock.picking', 'Rejected Deliver', readonly=True)
    rework_deliver_id = fields.Many2one('stock.picking', 'Rework Deliver', readonly=True)
    
    @api.multi
    def confirm(self):
        for line in self:
            line.write({'state': 'confirmed'})
        return True
    

