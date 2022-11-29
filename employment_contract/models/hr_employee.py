from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError, ValidationError
from docx import Document
import io
import json
import requests
from odoo.modules.module import get_module_resource
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
import base64
from datetime import date, datetime, time, timedelta

_logger = logging.getLogger(__name__)

class Employee(models.Model):    
    _inherit = 'hr.employee'  
    
    def get_employee_info(self, employee):
        
        emp = self.env['hr.employee'].sudo().browse(employee)
        contract = self.env['hr.contract'].search([('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1)
        if not contract:
            raise ValidationError(_("There is not contract for %s!!") % emp.name)
        
        start_date = (datetime.strptime(str(contract.date_start), '%Y-%m-%d').strftime("%Y-%m-%d")) if contract.date_start else ''
        trial_end_date = (datetime.strptime(str(contract.trial_date_end), '%Y-%m-%d').strftime("%Y-%m-%d")) if contract.trial_date_end else ''
        joining_date = (datetime.strptime(str(emp.joining_date), '%Y-%m-%d').strftime("%Y-%m-%d")) if emp.joining_date else ''
        wage = int(contract.wage)
        
        res = {
            'NAME': emp.name or '',
            'NRIC': emp.nrc or '',
            'JOBPOSITION': emp.job_id.name or '',
            'DEPARTMENT': emp.department_id.name or '',
            'JOB_DESC': emp.job_id.jd_summary or '',
            'START_DATE': start_date,
            'TRAIL_END_DATE': trial_end_date,
            'JOINT_DATE': joining_date,
            'SALARY': str(wage),
        }
        return res
                
    def download_contract(self):
        
        if self.state == 'probation':
            raise ValidationError(_("%s is not permanent!!") % self.name)
        contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
        # if not contract:
        #     raise ValidationError(_("There is not contract for %s!!") % self.name)
        # url = '/web/binary/download_docx_report/%s/%s' % (self.id,self.name)
        # return {
        #         'type': 'ir.actions.act_url',
        #         'url': url,
        #         'target': 'self',
        #         'res_id': self.id,
        #     }

        if not contract:
            raise ValidationError(_("There is not contract for %s!!") % self.name)
        url = '/web/binary/download_docx_template_report/%s/%s/%s' % (self.id, self.name, "Employee Contract")
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
            'res_id': self.id,
        }
class ContractConfig(models.Model):
    _name = 'contract.config'

    name = fields.Char(String='Contract Name')

    employee = fields.Many2one('hr.employee',string='Employee Name')
    contract_file = fields.Binary(string='Contract File')
    

    @api.constrains('contract_file')
    def check_contract(self):
        # import pdb
        # pdb.set_trace()
        
        datas = self.contract_file
        if datas:
        

            attachment = self.env['ir.attachment'].create({
                'name': "Employment Contract",
                'datas': datas,
                'type': 'binary',
                'res_model':'contract.config',
                'res_id': self.id,
                'company_id':False,
            })


class DocumentTemplateConfig(models.Model):
    _name = 'document.template.config'

    name = fields.Char(String='Template Name')

    employee = fields.Many2one('hr.employee', string='Employee Name')
    template_file = fields.Binary(string='Contract File')
    template_lines = fields.One2many('document.template.line', 'document_template_id', string='Template Line',copy=True, auto_join=True)

    @api.constrains('template_file')
    def check_contract(self):
        # import pdb
        # pdb.set_trace()

        datas = self.template_file
        if datas:
            attachment = self.env['ir.attachment'].create({
                'name': self.name,
                'datas': datas,
                'type': 'binary',
                'res_model': 'document.template.config',
                'res_id': self.id,
                'company_id': False,
            })

class DocumentTemplateLine(models.Model):
    _name = 'document.template.line'
    document_template_id = fields.Many2one('document.template.config', string='Template Reference', required=True,
                                           ondelete='cascade', index=True,
                                           copy=False)
    model_name = fields.Many2one('ir.model', help="Choose the model name", string="Model", required=True)
    model_field = fields.Many2one('ir.model.fields', string='Field', help="Choose the field",
                                  domain="[('model_id', '=',model_name)]",
                                  required=True)
    column_name = fields.Char(String='Column Name',store=True, readonly=False,
        compute='_compute_model_field_change')

    @api.depends('model_field')
    def _compute_model_field_change(self):
        if not self.model_field:
            return
        for record in self:
            record.column_name = '#' + str(record.model_field.name)