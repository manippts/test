import odoo
from odoo import api, fields, models, _  # alphabetically ordered
from odoo.exceptions import UserError
from datetime import datetime
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta


import odoo.addons.decimal_precision as dp

class CrmClaimStage(models.Model):
    """ Model for claim stages. This models the main stages of a claim
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.claim.stage"
    _description = "Claim stages"
    _rec_name = 'name'
    _order = "sequence"

#     @api.model
#     def _get_claim_type(self):
#         return self.env['crm.claim']._get_claim_type()


    name = fields.Char('Stage Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Used to order stages. Lower is better.", default=1)
    section_ids = fields.Many2many('crm.team', 'section_claim_stage_rel', 'stage_id', 'section_id', string='Sections',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams.")
    case_default = fields.Boolean('Common to All Teams',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams.")
#     claim_type = fields.Many2one('crm.claim.type',
#                         selection=_get_claim_type,
#                         help="Claim classification")
    claim_common = fields.Boolean(string='Common to All Claim Types',
                                  help="If you check this field,"
                                  " this stage will be proposed"
                                  " by default on each claim type.")

class CrmCaseCateg(models.Model):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"
    
    name = fields.Char('Name', required=True, translate=True)
    section_id = fields.Many2one('crm.team', 'Sales Team')
    object_id = fields.Many2one('ir.model', 'Object Name')
       
       
class CrmClaimType(models.Model):
    """
        CRM Claim Type
    """
    _name = 'crm.claim.type'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    
class CrmClaim(models.Model):
    """ Crm claim
    """
    _name = "crm.claim"
    _description = "Claim"
    _order = "priority,date desc"
    _inherit = ['mail.thread']

    @api.multi
    def _get_default_warehouse(self):
        company_id = self.env.user.company_id.id
        wh_obj = self.env['stock.warehouse']
        wh = wh_obj.search([('company_id', '=', company_id)], limit=1)
        if not wh:
            raise UserError(('There is no warehouse for the current user\'s company.'))
        return wh

#     def _get_default_section_id(self, cr, uid, context=None):
#         """ Gives default section by checking if present in the context """
#         return self.pool.get('crm.lead')._resolve_section_id_from_context(cr, uid, context=context) or False
# 
#     def _get_default_stage_id(self, cr, uid, context=None):
#         """ Gives default stage_id """
#         section_id = self._get_default_section_id(cr, uid, context=context)
#         return self.stage_find(cr, uid, [], section_id, [('sequence', '=', '1')], context=context)

    id = fields.Integer('ID', readonly=True)
    name = fields.Char('Claim Subject', required=True)
    active = fields.Boolean('Active', default="True")
    action_next = fields.Char('Next Action')
    date_action_next = fields.Datetime('Next Action Date')
    description = fields.Text('Description')
    resolution = fields.Text('Resolution')
    create_date = fields.Datetime('Creation Date' , readonly=True)
    write_date = fields.Datetime('Update Date' , readonly=True)
    date_deadline = fields.Date('Deadline')
    date_closed = fields.Datetime('Closed', readonly=True)
    date = fields.Datetime('Claim Date', select=True, default=fields.Datetime.now())
#     ref fields.reference('Reference', selection=openerp.addons.base.res.res_request.referencable_models),
    categ_id = fields.Many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.claim')]")
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', default='1')
    type_action = fields.Selection([('correction', 'Corrective Action'), ('prevention', 'Preventive Action')], 'Action Type')
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='always', default=lambda self: self.env.user)
    user_fault = fields.Char('Trouble Responsible')
    section_id = fields.Many2one('crm.team', 'Sales Team', \
                        select=True, help="Responsible sales team."\
                                " Define Responsible user and Email account for"\
                                " mail gateway.")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('crm.lead'))
    partner_id = fields.Many2one('res.partner', 'Partner')
    email_cc = fields.Text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    email_from = fields.Char('Email', size=128, help="Destination email for email gateway.")
    partner_phone = fields.Char('Phone')
    stage_id = fields.Many2one ('crm.claim.stage', 'Stage', track_visibility='onchange')
    cause = fields.Text('Root Cause')
    
    claim_type = fields.Many2one('crm.claim.type', help="Claim classification")
    serial_no = fields.Many2one('stock.production.lot', 'Serial Number')
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   required=True,
                                   default=_get_default_warehouse)
    rma_number = fields.Char(size=128, help='RMA Number provided by supplier')
    product_id = fields.Many2one('product.product', "Product", store=True)
    product_qty = fields.Float('Product Quantity', digits=dp.get_precision('Product Unit of Measure'), default=0.0, required=True, readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', readonly=False,
            help="Bill of Materials allow you to define the list of required raw materials to make a finished product.")
    warranty_status = fields.Selection([('not_sold', 'Not Sold'),
                                            ('under_warranty', 'Under Warranty'),
                                            ('out_of_warranty', 'Out of Warranty'),
                                            ], string="Warranty Status", readonly=True, store=True)
                
    claim_warranty_ids = fields.One2many('claim.warranty', 'claim_warranty_id', 'Warranty Period', store=True)
    spare_ids = fields.One2many('crm.claim.spares', 'claim_id', 'Spares')
    invoice_ids = fields.One2many('account.invoice', 'claim_id', 'Refunds',
                                  copy=False)
    picking_ids = fields.One2many('stock.picking', 'claim_id', 'RMA', copy=False)
    material_req_id =fields.Many2one('indent.indent', 'Material Requisition',copy=False)
    sale_order_spare_id = fields.Many2one('sale.order','Spare Order')
    department_id = fields.Many2one('hr.department','Department')
    
    @api.onchange('serial_no')
    def onchange_serial_id(self):
        warrenty_line = [] 
        if self.serial_no:
            line = self.serial_no
            product_id = line.product_id.id
            warranty = line.warranty_status
            partner_id = line.partner_id.id
            for wr in line.warranty_ids:
                start_date = wr.start_date
                end_date = wr.end_date
                warrenty_line.append((0, 0, {'w_start_date': start_date, 'w_end_date': end_date}))
                
            order_lines = self.env['sale.order.line'].search([('product_tmpl_id', '=', product_id)])
            count = 0
            for order_line in order_lines:
                count = count + order_line.product_uom_qty
            self.product_qty = count
            self.claim_warranty_ids = warrenty_line
            self.product_id = product_id
            self.warranty_status = warranty
            self.partner_id = partner_id
    
    @api.model
    def create(self, vals):
        serial_obj = self.env['stock.production.lot']
        sale_line_obj = self.env['sale.order.line']
        serial_id = vals.get('serial_no')
        serial_br = serial_obj.browse(serial_id)
        order_lines = sale_line_obj.search([('product_tmpl_id', '=', serial_br.product_id.id)])
        count = 0
        for line in order_lines:
            count = count + line.product_uom_qty
        vals['product_qty'] =count
        vals['warranty_status'] =serial_br.warranty_status
        result = super(CrmClaim, self).create(vals)
        return result
    
    @api.multi
    def write(self, vals):
        serial_obj = self.env['stock.production.lot']
        sale_line_obj = self.env['sale.order.line']
        serial_id = vals.get('serial_no')
        serial_br = serial_obj.browse(serial_id)
        order_lines = sale_line_obj.search([('product_tmpl_id', '=', serial_br.product_id.id)])
        count = 0
        for line in order_lines:
            count = count + line.product_uom_qty
        vals['product_qty'] =count
        vals['warranty_status'] =serial_br.warranty_status
        result = super(CrmClaim, self).write(vals)
        return result
    
    @api.multi
    def action_create_service_qtn(self, vals):
        sale_obj = self.env['sale.order']
        for record in self:
            if not record.spare_ids:
                raise UserError(('Please select Spares!!'))
            lines = []
            for line in record.spare_ids:
                lines.append((0, 0, {'product_id': line.product_id.id, 'product_uom_qty': line.product_qty}))
            vals['partner_id'] = record.partner_id.id
            vals['order_line'] = lines
            sale_order_spare_id = sale_obj.create(vals)
            record.write({'sale_order_spare_id': sale_order_spare_id.id})
            form_view = self.env.ref('sale.view_order_form').id   
        return {
            'name': _('Spare Quotation'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': False,
            'views': [(form_view or False, 'form'),
                      (False, 'kanban'),
                      (False, 'calendar'), (False, 'graph')],
            'target': 'current',
            'res_id': sale_order_spare_id.id
            }
        
    @api.multi
    def action_view_service_qtn(self, vals):
        sale_order_spare_id = self[0].id
        form_view = self.env.ref('sale.view_order_form').id   
        
        return {
            'name': _('Spare Quotation'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': False,
            'views': [(form_view or False, 'form'),
                      (False, 'kanban'),
                      (False, 'calendar'), (False, 'graph')],
            'target': 'current',
            'res_id': sale_order_spare_id
            }


    def action_create_material_req(self, vals):
        material_obj = self.env['indent.indent']
        for record in self:
            if record.material_req_id:
                raise UserError(('Material Requisition already created.'))
            if not record.spare_ids:
                raise UserError(('Please select needed spares.'))
            lines = []
            for move_line in record.spare_ids:
                lines.append((0, 0, {'name' : record.name, 'product_id': move_line.product_id.id, 'qty_available': move_line.product_id.qty_available, 'virtual_available': move_line.product_id.virtual_available, 'product_uom_qty': move_line.product_qty, 'product_uom': move_line.product_id.uom_id.id, 'price_unit': move_line.product_id.standard_price}))
            vals['name'] = self.env['ir.sequence'].next_by_code('indent.indent') or '/'
            vals['origin'] = record.name
            vals['department_id']=record.department_id.id
            vals['purpose']='Service'
            vals['product_lines'] = lines
            material_req_id = material_obj.create(vals)
            record.write({'material_req_id': material_req_id.id})
        return True
    
    @api.multi
    def action_view_material_req(self):
        material_req_ids = self.mapped('material_req_id')
        imd = self.env['ir.model.data']
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
        if len(material_req_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % material_req_ids.ids
        elif len(material_req_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = material_req_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
 
class ProductWarranty(models.Model):
    _name = "product.warranty"

    _rec_name = 'warranty_id'
    _order = 'start_date'
    _order = 'id desc'

    start_date = fields.Date("Warranty Start Date")
    end_date = fields.Date("Warranty End Date")
    
    warranty_id = fields.Many2one("stock.production.lot", string='Serial Number')
    
class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    
    
    def _get_warranty_status(self):
        warranty_date = self.warranty_end_date
        if warranty_date:
            warranty_end_date = datetime.strptime(warranty_date, "%Y-%m-%d").date()
            for line in self:
                if warranty_end_date >= datetime.today().date():
                    line.warranty_status = 'under_warranty'
                else:
                    line.warranty_status = 'out_of_warranty'
        return 
     
   
    partner_id = fields.Many2one('res.partner', string='Partner')
    
    warranty_status = fields.Selection([('not_sold', 'Not Sold'),
                                            ('under_warranty', 'Under Warranty'),
                                            ('out_of_warranty', 'Out of Warranty'),
                                            ], compute=_get_warranty_status, string="Warranty Status")
    warranty_ids = fields.One2many('product.warranty', 'warranty_id', string='Warranty History')
    warranty_end_date = fields.Date(string='Warranty End Date')
   
   

class CrmClaimSpares(models.Model):
    _name = 'crm.claim.spares'
    
    product_id = fields.Many2one('product.product', "Product")
    product_qty = fields.Float('Product Quantity', digits=dp.get_precision('Product Unit of Measure'), default=1.0, required=True)
    claim_id = fields.Many2one('crm.claim', 'Product Name')
    
class ClaimWarranty(models.Model):
    _name = "claim.warranty"

    _rec_name = 'claim_warranty_id'
    _order = 'w_start_date'
    
    w_start_date = fields.Date('Warranty start Date')
    w_end_date = fields.Date('Warranty end Date')
    claim_warranty_id = fields.Many2one('crm.claim', 'Claim Reference')
    

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    claim_id = fields.Many2one('crm.claim', string='Claim')
                 
    @api.multi
    def action_invoice_open(self):
        serial_obj = self.env['stock.production.lot']
        product_obj = self.env['product.product']
        product_warranty = self.env['product.warranty']
        for invoice_line in self.invoice_line_ids:
            product_id = invoice_line.product_id.id
            product = product_obj.browse(product_id)
            prd_warranty = product.warranty
            if self.date_invoice:
                in_date = self.date_invoice
                invoice_date = datetime.strptime(in_date, "%Y-%m-%d").date()
                end_date = invoice_date + timedelta(int(prd_warranty) * 364 / 12)
            else:
                invoice_date = datetime.today().date()
                end_date = invoice_date + timedelta(int(prd_warranty) * 364 / 12)
        for line in self.invoice_line_ids:
            serial_name = line.lot_serial_ids.name
            stock_line = serial_obj.search([('name', '=', serial_name)])
            if stock_line:
                vals = {
                    'partner_id': line.partner_id.id,
                    'warranty_end_date':end_date
                    }
                stock_line.write(vals)
                w_history = {
                    'start_date':invoice_date,
                    'end_date':end_date,
                    'warranty_id':stock_line.id,
                    }
                warranty_history_id = product_warranty.create(w_history)
                
        return super(AccountInvoice, self).action_invoice_open()
             
        

class StockPicking(models.Model):
    _inherit = "stock.picking"
    claim_id = fields.Many2one('crm.claim', 'Claim')
