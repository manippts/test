import odoo
from odoo import api, fields, models # alphabetically ordered
from odoo.exceptions import UserError
from datetime import datetime

class Lead(models.Model):
    _inherit = "crm.lead"   
    
    crm_line_ids = fields.One2many('crm.order.line', 'crm_line_id')

class CrmOrderLine(models.Model):
    _name = "crm.order.line"
    
    product_id = fields.Many2one('product.product', string='Product',copy=False)
    name = fields.Text('Description')
    size = fields.Char('Size')
    product_uom_qty = fields.Float('Ordered Quantity')
    product_uom = fields.Many2one('product.uom', 'Unit of Measure')
    price_unit = fields.Float('Unit Price')
    tax_ids = fields.Many2many('account.tax', 'tax_pipe_line_rel', 'tax_id', 'pipe_line_id', string='Tax', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_subtotal = fields.Float('Subtotal')	
    crm_line_id = fields.Many2one('crm.lead')
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        """Bring values for description,price_unit,price_subtotal and product_uom_qty fields while selecting a product."""  
        if self.product_id:             
            self.price_unit = self.product_id.lst_price
            self.price_subtotal = self.product_id.lst_price
            name = self.product_id.name_get()[0][1]
            if self.product_id.description_sale:
                name += '\n' + self.product_id.description_sale
            self.name = name
            if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
                self.product_uom = self.product_id.uom_id
                self.product_uom_qty = 1.0

    @api.multi
    @api.onchange('product_uom_qty')
    def product_uom_qty_change(self): 
        """ Calculating subtotal for a product""" 
        if self.product_uom_qty:
            self.price_subtotal = self.product_uom_qty * self.price_unit
            
            
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    def _prepare_so_line_from_oppor_line(self, rec):
        vals = {
                'product_id':rec.product_id.id,
                'name':rec.name,
                'size':rec.size,
                'product_uom_qty':rec.product_uom_qty,
                'product_uom':rec.product_uom.id,
                'price_unit':rec.price_unit,           
                'tax_id': [(6, 0, rec.tax_ids.ids)],                          
                'price_subtotal':rec.price_subtotal,
                }
        return vals


    @api.onchange('opportunity_id')
    def opportunity_change(self):
        if not self.opportunity_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.opportunity_id.partner_id.id

        new_lines = self.env['sale.order.line']
        for line in self.opportunity_id.crm_line_ids:
            data = self._prepare_so_line_from_oppor_line(line)
            new_line = new_lines.new(data)
            new_lines += new_line

        self.order_line += new_lines
        return {}