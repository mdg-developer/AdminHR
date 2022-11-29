from odoo import fields, models


class EmployeeTaxInfo(models.Model):    
    _inherit = 'hr.employee'    
    _description = 'Employee Tax Information'

    branch_id = fields.Many2one('res.branch', string='Branch', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    spouse_exemption = fields.Boolean(string='Tax Exemption for Spouse')
    father_exemption = fields.Boolean(string='Tax Exemption for Father')
    mother_exemption = fields.Boolean(string='Tax Exemption for Mother')
    father_name = fields.Char(string='Father Name')
    mother_name = fields.Char(string='Mother Name')
    salary_total = fields.Float(string='Previous Income Total')
    tax_paid = fields.Float(string='Previous Tax Paid')
    financial_year = fields.Many2one('account.fiscal.year', string='Financial Year')
# '|', ('company_id', '=', False), ('company_id', '=', company_id), '|', ('branch_id', '=', False), 