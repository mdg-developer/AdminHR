from odoo import fields, models, api, _


class Department(models.Model):
    _inherit = "hr.department"

    employee_ids = fields.One2many('hr.employee', 'department_id', string='Employees')
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    job_id = fields.Many2one('hr.job', string='Job Position')
    analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag')
    approve_manager = fields.Many2one('hr.employee', string='Approve Manager')


class HrSection(models.Model):
    _name = "hr.employee.section"
    _description = "Section"
    _rec_name = "name"

    name = fields.Char(string="Name")
    department_id = fields.Many2one('hr.department', "Department", required=True)
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')


class HrTeam(models.Model):
    _name = "hr.employee.team"
    _description = "Team"
    _rec_name = "name"

    name = fields.Char(string="Name")
    section_id = fields.Many2one('hr.employee.section', "Section", required=True)
    department_id = fields.Many2one('hr.department', "Department")
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
