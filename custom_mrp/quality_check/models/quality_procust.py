import time
from datetime import datetime
from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp
from collections import Counter


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qual_check = fields.Boolean('Quality Check')        
    quality_check = fields.Many2one('stock.location')


# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#     _table = "product_product"
#     _description = 'Quality Checking'

#     qual_check = fields.Boolean('Quality Check')        
#     quality_check = fields.Many2one('stock.location')


class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    quality_id = fields.Many2one('quality.accept', 'Quality')

class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    quality_check = fields.Boolean('quality')
