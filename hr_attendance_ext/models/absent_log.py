from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class absent_log(models.Model):
    _name = "absent.log"
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    company_id = fields.Many2one('res.company', string='Company')
    date = fields.Date(string="Date")
    log = fields.Char('Log')