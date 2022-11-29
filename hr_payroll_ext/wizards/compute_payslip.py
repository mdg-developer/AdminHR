import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ComputePayslip(models.TransientModel):
    _name = "compute.payslip"

    confirm = fields.Boolean('Confirm', default=True)
    
    def compute_payslip(self):
        payslips = self.env['hr.payslip'].browse(self._context.get('active_ids', []))
        for payslip in payslips:
            if payslip.state == 'draft':
                payslip.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}