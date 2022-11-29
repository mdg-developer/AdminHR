from odoo import fields, models

class Branch(models.Model):    
    _inherit = 'res.branch' 
    
    hr_manager_id  = fields.Many2one('hr.employee', string='HR Manager',tracking=True)