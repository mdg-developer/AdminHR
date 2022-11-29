import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class DraftPayslip(models.TransientModel):
    _name = "draft.payslip"

    confirm = fields.Boolean('Confirm', default=True)
    
    def set_to_draft(self):
        payslips = self.env['hr.payslip'].browse(self._context.get('active_ids', []))
        for payslip in payslips:
            if payslip.state == 'cancel':
                payslip.action_payslip_draft()
        return {'type': 'ir.actions.act_window_close'}