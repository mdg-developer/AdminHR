from odoo import api, models, fields, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    slip_day_of_month = fields.Float(strig='Total Days', readonly=True)

    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_slip_days(self):
        if self.date_from and self.date_to:
            self.slip_day_of_month = (self.date_to - self.date_from).days + 1
        else:
            self.slip_day_of_month = 0
