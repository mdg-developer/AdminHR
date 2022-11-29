from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta


class HRLogisticsCommission(models.Model):    
    _name = 'hr.logistics.commission'
    _description = 'HR Logistics Commission'    

    employee_id = fields.Many2one('hr.employee', string='Employee')
    commission = fields.Float(string='Commission')
    from_datetime = fields.Datetime(string='From Datetime')
    to_datetime = fields.Datetime(string='To Datetime')
    trip_code = fields.Char(string='Trip Code')
    state = fields.Selection([('draft', 'Draft'),
                            ('posted', 'Posted'),
                            ('cancel', 'Cancelled')], string='Status', default='draft')
    