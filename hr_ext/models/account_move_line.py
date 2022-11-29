from odoo import models, api, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', domain="[('company_id', '=', company_id)]")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.account_id = self.product_id.property_account_expense_id.id if self.product_id.property_account_expense_id else False
            if self.move_id.partner_id:
                partner = self.move_id.partner_id
                employee = self.env['hr.employee'].sudo().search([('address_home_id', '=', partner.id)], limit=1)
                if employee:
                    self.analytic_account_id = employee.branch_id.analytic_account_id.id if employee.branch_id.analytic_account_id else False
                    self.analytic_tag_ids = [(4, employee.department_id.analytic_tag_id.id if employee.department_id.analytic_tag_id else False)] 