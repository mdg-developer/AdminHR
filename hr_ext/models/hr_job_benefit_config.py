from odoo import api, fields, models, _


class HrJobBenefitConfig(models.Model):    
    _name = 'hr.job.benefit.config'
    _description = 'Job Benefit Configuration'
    
    name = fields.Char(string='Name', required=True)