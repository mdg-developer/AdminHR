from odoo import fields, models, api, _
from datetime import date, datetime, timedelta
import base64
import re
from odoo.exceptions import UserError, ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    state = fields.Selection([('probation', 'Probation'),('extend_probation', 'Extended Probation'), ('permanent', 'Permanent')], 'State', default='probation')
    permanent_date = fields.Date(string='Permanent Date', readonly=True)


    def print_probation_confirm(self):
        pdf_file = self.env.ref('hr_ext.hr_employee_probation').report_action(self)

        #return pdf_file

        contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
        if not contract:
            raise ValidationError(_("There is not contract for %s!!") % self.name)
        url = '/web/binary/download_docx_template_report/%s/%s/%s' % (self.id,self.name,"Probation Confirmation")
        return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'self',
                'res_id': self.id,
            }


    def print_employee_offer(self):
        
        #pdf_file = self.env.ref('hr_ext.hr_employee_offer').report_action(self)
        #return pdf_file

        contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
        if not contract:
            raise ValidationError(_("There is not contract for %s!!") % self.name)
        url = '/web/binary/download_docx_template_report/%s/%s/%s' % (self.id, self.name, "Offer Letter")
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
            'res_id': self.id,
        }


    def print_extend_probation(self):
        contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
        if not contract:
            raise ValidationError(_("There is not contract for %s!!") % self.name)
        url = '/web/binary/download_docx_template_report/%s/%s/%s' % (self.id, self.name, "Extend Probation")
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
            'res_id': self.id,
        }
        #pdf_file = self.env.ref('hr_ext.hr_employee_extend_probation').report_action(self)
# return pdf_file
        
        
        
