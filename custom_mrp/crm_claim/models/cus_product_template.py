import odoo
from odoo import api, fields, models,_ # alphabetically ordered
from odoo.exceptions import UserError
from datetime import datetime

class ProductTemplate(models.Model):  
    _inherit = 'product.template'
    
#     @api.model
#     
#     def create(self, vals):  
#         if not vals['warranty']:
#             raise UserError(_('Warrenty Should be Entered.'))
#         return super(ProductTemplate, self).create(vals)
#      
#     @api.multi
#     def write(self, vals):
#         
#         if not self.warranty:
#             raise UserError(_('Warrenty Should be Entered.'))
#         return super(ProductTemplate, self).write(vals)
          
     