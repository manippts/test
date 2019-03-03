# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    @api.multi
    @api.depends('sale_line_id')
    def _compute_picking_number(self):
        procurement_obj = self.env['procurement.order']
        stock_move_obj = self.env['stock.move']
        for invoice_line in self:
            if invoice_line.sale_line_id:
                procurement_br = procurement_obj.search([('sale_line_id', '=', invoice_line.sale_line_id.id)])
                if procurement_br:
                    stock_move_br = stock_move_obj.search([('procurement_id', '=', procurement_br[0].id)])
                    if stock_move_br:
                        invoice_line.related_move_id = stock_move_br[0].id
                        invoice_line.write({'ref_related_move_id': stock_move_br[0].id})
#                         print stock_move_br
#                         raise UserError(stock_move_br)
                        if stock_move_br.quant_ids:
                            for quant in stock_move_br.quant_ids:
                                print quant
                                invoice_line.write({'lot_serial_ids': [(4, quant.lot_id.ids)]})
                    
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Line Id')
    related_move_id = fields.Many2one('stock.move', string='#Move', compute="_compute_picking_number")
    ref_related_move_id = fields.Many2one('stock.move', string='#Move1')
    lot_serial_ids = fields.Many2many('stock.production.lot', string='Lot/Serial Number')
    
    
    
    

    