from odoo import api, fields, models, _


# class Employee(models.Model):
#     _inherit = 'hr.employee'
# 
#     dotted_line_manager_id = fields.Many2one('hr.employee', string='Dotted Line Manager')
#     approve_manager = fields.Many2one('hr.employee', string='Approve Manager')

class HrEmployeePublic(models.Model):
    _inherit = ["hr.employee.public"]

    dotted_line_manager_id = fields.Many2one('hr.employee.public', string='Dotted Line Manager')
    approve_manager = fields.Many2one('hr.employee.public', string='Approve Manager')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)