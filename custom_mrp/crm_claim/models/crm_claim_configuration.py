import odoo
from odoo import api, fields, models # alphabetically ordered
from odoo.exceptions import UserError
from datetime import datetime

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
    section_ids = fields.Many2many('crm.case.section', 'section_claim_stage_rel', 'stage_id', 'section_id', string='Sections',
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
    section_id = fields.Many2one('crm.case.section', 'Sales Team')
    object_id = fields.Many2one('ir.model', 'Object Name')
       
       
class CrmClaimType(models.Model):
    """
        CRM Claim Type
    """
    _name = 'crm.claim.type'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    
