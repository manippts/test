from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.fields import Many2one

class IndentIndent(models.Model):
    _name = 'indent.indent'
    _inherit = ['mail.thread']
    _description = 'Indent'
    
    @api.multi
    def _default_stock_location(self):
        #TODO: need to improve this try except with some better option
        warehouse_id = self._get_default_warehouse()
        if warehouse_id:
            return warehouse_id and warehouse_id.int_type_id.default_location_dest_id.id
        return False

    @api.multi
    def _default_src_stock_location(self):
        #TODO: need to improve this try except with some better option
        warehouse_id = self._get_default_warehouse()
        if warehouse_id:
            return warehouse_id and warehouse_id.lot_stock_id.id
        return False
    
    @api.model
    def _get_default_warehouse(self):
        warehouse_obj = self.env['stock.warehouse']
        company_id = self.env.user.company_id
        warehouse_ids = warehouse_obj.search([('company_id', '=', company_id.id)])
        warehouse_id = warehouse_ids and warehouse_ids[0] or False
        return warehouse_id
    
    @api.model
    def _get_default_picking_type(self):
        warehouse_id = self._get_default_warehouse()
        if warehouse_id:
            return warehouse_id and warehouse_id.int_type_id.id
        picking_type_obj = self.env['stock.picking.type']
        picking_type_ids = picking_type_obj.search([('code', '=', 'internal')])
        picking_type_id = picking_type_ids and picking_type_ids[0] or False
        return picking_type_id
    
    @api.depends('in_picking_id.state')       
    def _check_product_return_status(self):
        result = {}
        picking_obj = self.env['stock.picking']
        for indent in self:
            picking_ids = []
            flag = False
            if indent.in_picking_id and indent.in_picking_id.state == 'done':
                flag = True
                backorder_search = picking_obj.search([('backorder_id', '=', indent.in_picking_id.id)])
                backorder_search += picking_obj.search([('indent_id', '=', indent.id), ('indent_return', '=', True)])
                if backorder_search:
                    for order in backorder_search:
                        if order.state != 'done':
                            flag = False
            self.product_return_status = flag
            
    name = fields.Char('Reference', default='/')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('waiting_approval', 'Waiting for Approval'),
        ('inprogress', 'In Progress'),
        ('received', 'Issued'),
        ('reject', 'Rejected'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    indentor_id = fields.Many2one('res.users', 'Indentor', readonly=True, default=lambda self: self.env.user)
    department_id = fields.Many2one('hr.department', 'Department', required=True, readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)]})
    manager_id = fields.Many2one(related='department_id.manager_id', readonly=True, string='Department Manager', store=True, states={'draft': [('readonly', False)]})
    approver_id = fields.Many2one('res.users', 'Authority', readonly=True, track_visibility='always', states={'draft': [('readonly', False)]}, help="who have approve or reject indent.", default=False)
    purpose = fields.Char('Purpose', required=True, readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)]})
    src_location_id = fields.Many2one('stock.location', 'Source Location', required=True, readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)]}, default=_default_src_stock_location)
    location_id = fields.Many2one('stock.location', 'Destination Location', required=True, readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)]}, default=_default_stock_location)
    indent_date = fields.Datetime('Indent Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    required_date = fields.Datetime('Required Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    approve_date = fields.Datetime('Approve Date', readonly=True, track_visibility='onchange')
    requirement = fields.Selection([('1', 'Ordinary'), ('2', 'Urgent')], 'Requirement', readonly=True, required=True, track_visibility='onchange', states={'draft': [('readonly', False)]}, default='1')
    type = fields.Selection([('stock', 'Stock'), ('purchase', 'Purchase Indent')], 'Type', required=True, track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]}, default='stock')
    move_type = fields.Selection([('direct', 'Partial'), ('one', 'All at once')], 'Receive Method', track_visibility='onchange', readonly=True, required=True, states={'draft':[('readonly', False)], 'cancel':[('readonly',True)]}, help="It specifies goods to be deliver partially or all at once", default='one')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="default warehose where inward will be taken", readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=_get_default_warehouse)
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, required=True, default=_get_default_picking_type)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('indent.indent'))
    product_lines = fields.One2many('indent.product.lines', 'indent_id', 'Products')
    picking_id = Many2one('stock.picking', 'Picking')
    in_picking_id = fields.Many2one('stock.picking','Picking')
    active = fields.Boolean('Active', default=True)
    requisition_id = fields.Many2one('purchase.requisition', 'Purchase Indent', copy=False)
    product_return_status = fields.Boolean(compute="_check_product_return_status", store=False, string="Products Returned ?")
    origin = fields.Char("Origin")
    # Onchange for department to return the department location as destination location
    @api.multi
    @api.onchange('department_id')
    def onchange_department_id(self):
        if self.department_id:
            self.location_id = self.department_id.location_dest_id.id
           
    @api.multi
    def indent_confirm(self):
        for indent in self: 
            if not indent.product_lines:
                raise UserError(_('You cannot confirm an indent %s which has no line.' % (indent.name)))
            # Add all authorities of the indent as followers
            followers = []
            if indent.indentor_id and indent.indentor_id.partner_id and indent.indentor_id.partner_id.id:
                followers.append(indent.indentor_id.partner_id.id)
            if indent.manager_id and indent.manager_id.user_id.partner_id and indent.manager_id.user_id.partner_id.id:
                followers.append(indent.manager_id.user_id.partner_id.id)

            for follower in followers:
                indent.write({'message_follower_ids': [(4, follower)]})
            indent.write({'state': 'waiting_approval'})
        return True
    
    @api.multi
    def indent_reject(self):
        self.write({'state':'reject','approver_id': self.env.user.id, 'approve_date': fields.Datetime.now(), 'active':False})
    
    @api.multi
    def action_picking_purchase_create(self):
        if self.type == 'stock':
            self.action_picking_create()
        elif self.type == 'purchase':
            self.create_purchase_requisition()
            self.action_picking_create()
            self.write({'state': 'inprogress'})
        return True
     
    @api.multi
    def action_picking_create(self):
        move_obj = self.env['stock.move']
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        picking_id = False
        indent = self
#         indent = self.browse(cr, uid, ids[0], context=context)
 
        product_lines = [val for val in self.product_lines]
 
        if product_lines:
            picking_id = self._create_pickings_and_procurements(indent, product_lines, None)
 
        move_ids = move_obj.search([('picking_id','=',picking_id.id)])
 
        self.write({'picking_id': picking_id.id, 'state' : 'inprogress', 'approver_id': self.env.user.id, 'approve_date': fields.Datetime.now(),  'message_follower_ids': [(4, self.approver_id and self.approver_id.partner_id and self.approver_id.partner_id.id)]})
         
        return_product_lines = [val for val in self.product_lines if val.return_type == 'return']
        if return_product_lines:
            self.create_transfer_move(indent, return_product_lines, True)
            
        old_return_product_lines = [val for val in self.product_lines if val.return_type == 'non_return_old']
        if old_return_product_lines:
            self.create_transfer_move(indent, old_return_product_lines, True)
        return picking_id
    
    #for Non-Return
    @api.multi
    def _create_pickings_and_procurements(self, indent, product_lines, picking_id=False,):
        move_obj = self.env['stock.move']
        picking_obj = self.env['stock.picking']
        procurement_obj = self.env['procurement.order']
        proc_ids = []
 
        for line in product_lines:
#             date_planned = self._get_date_planned(cr, uid, indent, line, indent.indent_date, context=context)
 
            if line.product_id:
                move_id = False
                if not picking_id:
                    picking_id = picking_obj.create(self._prepare_indent_picking(indent, False))
                move_id = move_obj.create(self._prepare_indent_line_move(indent, line, picking_id))
#                 print move_id
        if picking_id:
            picking_id.action_confirm()
#             workflow.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        return picking_id
    
    @api.multi
    def _prepare_indent_picking(self, indent, indent_return):
        location_id = indent.src_location_id.id
        # pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking')
        res = {
#             'invoice_state': 'none',
            'picking_type_id': indent.picking_type_id.id,
            'priority': indent.requirement,
            'name': '/',
            'origin': indent.name,
            'date': indent.indent_date,
            'indent_return': indent_return,
            'move_type':indent.move_type,
            'partner_id': indent.indentor_id.partner_id.id or False,
            'indent_id': indent.id,
            'company_id': indent.company_id.id,
            'location_id': location_id,
            'location_dest_id': indent.location_id.id,
        }
        if indent.company_id:
            res = dict(res, company_id = indent.company_id.id)
        return res
    
    @api.multi
    def _prepare_indent_line_move(self, indent, line, picking_id):
        location_id = indent.src_location_id.id
        res = {
            'name': line.name,
            'indent_line_id':line.id,
            'picking_id': picking_id.id,
            'picking_type_id': self.picking_type_id.id or False,
            'product_id': line.product_id.id,
            'date': fields.Datetime.now(),
            'date_expected': fields.Datetime.now(),
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'location_id': location_id,
            'location_dest_id': indent.location_id.id,
            'department_id': indent.department_id.id,
            'origin': indent.name,
            'state': 'draft',
            'price_unit': line.product_id.standard_price or 0.0,
#             'company_id' : self.company_id.id 
        }

        if line.product_id.type in ('service'):
            if not line.original_product_id:
                raise UserError(_('You must define material or parts that you are going to repair !'))
                
            upd_res = {
                'product_id':line.original_product_id.id,
                'product_uom': line.original_product_id.uom_id.id,
                'product_uos':line.original_product_id.uom_id.id
            }
            res.update(upd_res)

        if indent.company_id:
            res = dict(res, company_id = indent.company_id.id)
        return res
    
    #For Return
    @api.multi
    def create_transfer_move(self, indent, return_product_lines, internal=None):
        move_obj = self.env['stock.move']
        picking_obj = self.env['stock.picking']
        product_pool = self.env['product.product']
        location_id = self.src_location_id.id
        picking_id = False
        for line in return_product_lines:
#             date_planned = self._get_date_planned(cr, uid, indent, line, line.return_date, context=context)
            if line.product_id:
                move_id = False
                if not picking_id:
                    picking_id = picking_obj.create(self._prepare_indent_picking(indent, True))
                    picking_id.update({
                        'location_id': indent.location_id.id,
                        'location_dest_id': location_id
                    })
                res = self._prepare_indent_line_move(indent, line, picking_id)
                res.update({
                    'location_id': indent.location_id.id,
                    'location_dest_id': location_id
                })
                move_id = move_obj.create(res)
        if picking_id:
            picking_id.action_confirm()
        self.write({'in_picking_id': picking_id.id, 'approver_id': self.env.user.id, 'approve_date': fields.Datetime.now()})
        return True
    
    #For Purchase Requisition
    @api.multi
    def create_purchase_requisition(self):
        for val in self:
            req_id = self._create_purchase_req(val)
            for line in val.product_lines:
                self._create_purchase_req_line(val, line, req_id)
            self.write({'requisition_id': req_id.id})
        return True
    
    @api.multi
    def _create_purchase_req(self, val):
        purchase_requisition_obj = self.env['purchase.requisition']
        values = {
            'name': '/',
            'origin':'Indent : ' + val.name,
            'user_id': self.env.user.id,
#             'exclusive': 'exclusive',
            'department_id': self.department_id.id,
#             'purpose': self.purpose,
            'ordering_date': fields.Datetime.now(),
        }
        res = purchase_requisition_obj.create(values)        
        return res
    
    @api.multi
    def _create_purchase_req_line(self, val, line, req_id):
        purchase_requisition_line_obj = self.env['purchase.requisition.line']
        values = {
            'name': line.product_id.name,
            'requisition_id': req_id.id,
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom_id': line.product_uom.id,
            'schedule_date': self.required_date or False,
        }
        res = purchase_requisition_line_obj.create(values)        
        return res
    
    @api.multi
    def open_purchase_requisition(self):
        '''
        This function returns an action that display internal move of given indent ids.
        '''
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('purchase_requisition.action_purchase_requisition')
        form_view_id = imd.xmlid_to_res_id('purchase_requisition.view_purchase_requisition_form')
        
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [form_view_id, 'form'],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if self.requisition_id.id:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = self.requisition_id.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    @api.multi
    def open_purchase_requisition_wizard(self):
        '''
        This function returns an action that display internal move of given indent ids.
        '''
        imd = self.env['ir.model.data']
        form_view_id = imd.xmlid_to_res_id('view_purchase_transfer_details')
        
        result = {
            'name': _('Purchase Requisition Details'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_view_id and form_view_id[1] or False,
            'res_model': 'purchase.requisition.details',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': False,
        }
        return result
    
    @api.multi
    def action_view_invoice(self):
        invoice_ids = self.mapped('invoice_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree1')
        list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.invoice_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(invoice_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
        elif len(invoice_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = invoice_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    #To view Receive products and Return Products
    @api.multi
    def _get_picking_id(self):
#         assert len(ids) == 1, 'This option should only be used for a single id at a time'
        picking_ids = []
#         indent = self.browse(cr, uid, ids[0], context=context)
        if not self.picking_id:
            raise UserError(_('No Products to be issued.'))
        picking_ids.append(self.picking_id.id)
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(picking_ids)
        picking_ids_search = picking_obj.search([('indent_id', '=', self.id), ('indent_return','=', False)])
        for pick in picking_ids_search:
            picking_ids.append(pick.id)
        return picking_ids
    
    @api.multi
    def action_receive_products(self):
        '''
        This function returns an action that display internal move of given indent ids.
        '''
        mod_obj = self.env['ir.model.data']
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        picking_ids = self._get_picking_id()
        #choose the view_mode accordingly
        if len(picking_ids) > 1:
            action['domain'] = [('id', 'in', picking_ids)]
        elif picking_ids:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = picking_ids and picking_ids[0] or False
        return action
    
    @api.multi
    def _get_return_picking_id(self):
#         assert len(ids) == 1, 'This option should only be used for a single id at a time'
        picking_ids = []
#         indent = self.browse(cr, uid, ids[0], context=context)
        if not self.in_picking_id:
            raise UserError(_('No Products to be returned.'))
        picking_ids.append(self.in_picking_id.id)
        picking_obj = self.env['stock.picking']
        picking_ids_search = picking_obj.search([('indent_id', '=', self.id), ('indent_return','=', True)])
        for pick in picking_ids_search:
            picking_ids.append(pick.id)
        return picking_ids
    
    @api.multi
    def action_products_return(self):
        '''
        This function returns an action that display internal move of given indent ids.
        '''
        mod_obj = self.env['ir.model.data']
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        picking_ids = self._get_return_picking_id()
        #choose the view_mode accordingly
        if len(picking_ids) > 1:
            action['domain'] = [('id', 'in', picking_ids)]
        elif picking_ids:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = picking_ids and picking_ids[0] or False
        return action
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('indent.indent') or '/'
        return super(IndentIndent, self).create(vals)
    
    @api.multi
    def unlink(self):
        for indent in self:
            if indent.state != 'draft':
                raise UserError(_('You can not delete a confirmed Indent.'))
        return super(IndentIndent, self).unlink()
    
class IndentProductLine(models.Model):
    _name = 'indent.product.lines'
    
    @api.depends('indent_id.picking_id')
    def _quantity_issued(self):
        result = {}
        stock_move_obj = self.env['stock.move']
        for line in self:
            if line.indent_id.picking_id:
                val = 0.0
                for record in stock_move_obj.search([('indent_line_id', '=', line.id), ('state', '=', 'done')]):
#                     stock_move = stock_move_obj.browse(record)
                    val += record.product_qty
                line.product_uom_qty_issued = val
    
    @api.depends('product_uom_qty', 'price_unit')
    def _amount_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_uom_qty * line.price_unit
    
    sequence = fields.Integer('Sequence')
    indent_id = fields.Many2one('indent.indent', 'Indent')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_qty = fields.Float('Quantity Required', digits=dp.get_precision('Product UoS'), required=True, default=1)
    qty_available = fields.Float('In Stock')
    name = fields.Text('Purpose', required=True)
    required_on = fields.Date('Required On')
    product_uom_qty_issued = fields.Float(compute="_quantity_issued", string='Quantity Issued', store=False)
    product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True)
    product_uos_qty = fields.Float('Quantity (UoS)' ,digits=dp.get_precision('Product UoS'), default=1)
    product_uos = fields.Many2one('product.uom', 'Product UoS')
    price_unit = fields.Float('Price', required=True, digits=dp.get_precision('Product Price'), help="Price computed based on the last purchase order approved.")
    price_subtotal = fields.Float(compute="_amount_subtotal", string='Subtotal', store=True)
    virtual_available = fields.Float('Forecasted Qty')
    delay = fields.Float('Lead Time', required=True, default=0.0)
    specification = fields.Text('Specification')
    sequence = fields.Integer('Sequence')
    return_type = fields.Selection([('non_return', 'Non-returnable'), ('return', 'Returnable'), ('non_return_old', 'Non-returnable with Receipt of Old Ones')], 'Return Type', required=True, default='non_return')
    product_returned = fields.Boolean('Product Returned', default=False)
    return_date = fields.Datetime('Return Date')
    indent_type = fields.Selection([('new', 'Purchase Indent'), ('existing', 'Repairing Indent')], 'Type')
    
    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        product_obj = self.env['product.product']
        if not self.product_id:
            return {'value': {'product_uom_qty': 1.0, 'product_uom': False, 'price_unit': 0.0, 'qty_available': 0.0, 'virtual_available': 0.0, 'name': '', 'delay': 0.0}}
        product = self.product_id        
        result['name'] = self.product_id.name
        result['product_uom'] = self.product_id.uom_id.id
        result['price_unit'] = self.product_id.standard_price
        result['qty_available'] = self.product_id.qty_available
        result['virtual_available'] = self.product_id.virtual_available        
        result['specification'] = self.product_id.name
        return {'value': result}
    
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    indent_return = fields.Boolean('Indent Returnable', default=False)
    indent_id = fields.Many2one('indent.indent', 'Indent')

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()
        if res:
            indent_obj = self.env['indent.indent']
            indent_line_obj = self.env['indent.product.lines']
#             picking = self.browse(cr, uid, picking_ids, context=context)[0]
            indent = self.indent_id
            if self.indent_id:
                issue_line_ids = []
                
#                 for move in self.move_lines:
#                     if move.state == 'done' and move.indent_line_id and (move.indent_line_id.return_type == 'non_return_old' and not move.indent_line_id.product_returned):
#                         issue_line_ids.append(move.indent_line_id)
# #                 print issue_line_ids[0]
#                 if issue_line_ids:
#                     picking_id = indent_obj._create_pickings_and_procurements(indent, issue_line_ids, None)
#                     self.write({'backorder_id': self.indent_id.picking_id.id})
#                     for i in issue_line_ids:
#                         i.write({'product_returned': True})
#                     .write([i.id for i in issue_line_ids], {'product_returned': True})
#                 indent_ids = self.get_indent_id(cr, uid, picking)
                picking_ids = []
                flag = False
                if indent.picking_id and indent.picking_id.state == 'done':
                    flag = True
                backorder_search = self.search([('backorder_id', '=', indent.picking_id.id)])
                backorder_search += self.search([('indent_id', '=', self.indent_id.id), ('indent_return', '=', False)])
                if backorder_search:
                    for order in backorder_search:
                        if order.state not in ('cancel', 'done'):
                            flag = False
                if flag:
                    self.indent_id.write({'state': 'received'})
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'

    indent_line_id = fields.Many2one('indent.product.lines', 'Indent Lines')
    indentor_id = fields.Many2one(related='indent_line_id.indent_id.indentor_id', string='Indentor', store=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='Department') 
    indent_date = fields.Datetime(related='indent_line_id.indent_id.indent_date', string='Indent Date', readonly=True)



class Department(models.Model):
    _inherit = "hr.department"
     
    location_dest_id = fields.Many2one('stock.location', string='Location')

