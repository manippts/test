import odoo
from odoo import api, fields, models  # alphabetically ordered
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta
import datetime
import dateutil


class QualityControlCalibration(models.Model):
    _name = "quality.control.calibration"
    _description = "Quality Control Calibration" 
    
    report_no = fields.Char("Calibration Report No")
    name = fields.Many2one('account.asset.asset',string='Instrument')
    code = fields.Char(string='Code')
    type = fields.Char(string='Type')
    range = fields.Char(string='Range')
    least_count = fields.Integer(string='Least Count')
    make = fields.Char(string='Make')
    date = fields.Date(string='Date Of Calibration')
    agency = fields.Many2one('res.partner',string='Calibration Agency')
    observed_error = fields.Char(string='Observed Error')
    error_limit = fields.Char(string='Acceptable Error Limit')
    model = fields.Char(string='Model')
    serial_no = fields.Char(string='Serial No')
    calibration_frequency = fields.Integer(string='Calibration Frequency')
    department = fields.Many2one('calibration.department',string='Department')
    calibration_cost = fields.Float(string='Calibration Cost')
    next_calibration_date = fields.Date(string='Next Calibration Date')
    checked_by = fields.Many2one('hr.employee',string='Checked by')
    remarks = fields.Text(string='Remarks')
    state = fields.Selection(
            [('draft', 'New'), ('in_progress', 'InProgress'),('confirm', 'Confirmed')],
            string='Status', readonly=True, default='draft')

    
    @api.onchange('name')
    def _onchange_name(self):
        
        self.range=self.name.range
        self.least_count=self.name.least_count
        self.serial_no=self.name.serial_no
        self.make=self.name.make
        self.model=self.name.model
        self.code=self.name.code
        self.calibration_frequency=self.name.calibration_frequency
        self.type=self.name.category_id.name
        
    @api.multi
    def calibrate(self):
        return self.write ({'state': 'in_progress'})
    
    @api.multi
    def confirm(self):
        calibration_history_obj = self.env['calibration.history']
        for record in self:
            current_date =  datetime.datetime.today().date()
            months = record.calibration_frequency
            next_calibration_date = current_date + relativedelta(months=months)

            history = {
                    'date':self.date,
                    'agency':self.agency,
                    'report_no':self.report_no,
                    'observed_error':self.observed_error,
                    'error_limit':self.error_limit,
                    'calibration_cost':self.calibration_cost,
                    'next_calibration_date':next_calibration_date,
                    'checked_by':self.checked_by,
                    'remarks':self.remarks,
                    'calibration_history_id':self.name.id
                }
            
            calibration_history_obj.create(history)
            record.write({'next_calibration_date': next_calibration_date})
        return self.write ({'state': 'confirm'})
      
      
    @api.model
    def create(self, vals):
        vals['report_no'] = self.env['ir.sequence'].get('calibration.seq') or '/'
        return super(QualityControlCalibration, self).create(vals)
    
    
    
class CalibrationDepartment(models.Model):
    _name = "calibration.department"
    _description = "Calibration Department" 
    
    name = fields.Char("Department")


class CalibrationHistory(models.Model):
    _name = "calibration.history"  
    
    date = fields.Date(string='Date Of Calibration')
    report_no = fields.Char("Calibration Report No")
    agency = fields.Char(string='Calibration Agency')
    observed_error = fields.Char(string='Observed Error')
    error_limit = fields.Char(string='Acceptable Error Limit')
    calibration_cost = fields.Float(string='Calibration Cost')
    next_calibration_date = fields.Date(string='Next Calibration Date')
    checked_by = fields.Char(string='Checked by')
    remarks = fields.Char(string='Remarks')  
    calibration_history_id = fields.Many2one("account.asset.asset",string='Calibration History')


class AccountAssetAsset(models.Model):
    _inherit = "account.asset.asset"   
    
    range = fields.Char(string='Range')
    least_count = fields.Integer(string='Least Count')
    serial_no = fields.Char(string='Serial No')
    make = fields.Char(string='Make')
    model = fields.Char(string='Model')
    calibration_frequency = fields.Integer(string='Calibration Frequency')
    calibration_history_ids = fields.One2many('calibration.history','calibration_history_id',string='Calibration History')

