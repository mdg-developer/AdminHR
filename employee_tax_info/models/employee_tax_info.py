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
    bus_stop_route = fields.Many2one('employee.bus.route', string='Bus Stop')
    ferry_car_no = fields.Many2one('fleet.vehicle')
    ferry_route_name = fields.Many2one('route.plan')


class EmployeeBus(models.Model):
    _name = 'employee.bus.route'

    name = fields.Char('Route')


class HrEmployeeBus(models.Model):
    _name = 'employee.bus'
    _description = 'Employee Bus'
