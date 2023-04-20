from odoo import fields, models, api, _


class ResBranch(models.Model):
    _inherit = 'res.branch'

    manager_id = fields.Many2one('hr.employee', 'Branch Manager',tracking=True)
    direct_manager_id = fields.Many2one('hr.employee', 'Direct Manager',tracking=True)

    @api.model
    def create(self, values):
        res = super(ResBranch, self).create(values)
        if values.get('manager_id') and values['manager_id']:
            employee = self.env['hr.employee'].browse(values['manager_id'])
            employee.is_branch_manager = True
            #employee.branch_id = res.id
        return res
    
    def write(self, values):
        res = super(ResBranch, self).write(values)
        if values.get('manager_id') and values['manager_id']:
            employee = self.manager_id
            employee.is_branch_manager = True
            #employee.branch_id = self.id
        return res

class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")