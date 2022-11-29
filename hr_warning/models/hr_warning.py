from odoo import api,fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone, UTC

class HRWarning(models.Model):    
    _name = 'hr.warning'
    _description = 'Warnings'
    _order = 'id desc'
    
    utc_time = fields.Datetime.now()
    tz = timezone('Asia/Yangon')
    name = fields.Char(string='Name', copy=False, readonly=True)
    date = fields.Date('Create Date',default= UTC.localize(utc_time, is_dst=None).astimezone(tz).date())
    employee_id = fields.Many2one('hr.employee', string='Employee')  
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
    department_id = fields.Many2one('hr.department', string='Department')
    description = fields.Char('Description')  
    warning_type_id = fields.Many2one('warning.type', string='Warning Type')
    warning_title_id = fields.Many2one('warning.title', string='Warning Title')
    mark = fields.Float('Mark')
    warning_no = fields.Char('Warning No')
    linked_warning_id = fields.Many2one('hr.warning','Linked Warning')
    manager_warning_ids = fields.One2many('hr.warning', 'linked_warning_id')
    temp_lines = fields.One2many('hr.warning.temp', 'warning_id')
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', ' Submitted'),
                              ('approve', 'Approved'),
                              ('decline', 'Declined'),
                              ('expire', 'Expired')], string='Status', readonly=True, index=True, copy=False,
                             default='draft', tracking=True)
    approved = fields.Boolean('Approved', copy=False, default=False)
    fiscal_year = fields.Many2one('account.fiscal.year', string='Fiscal Year')
    warn_date = fields.Date('Warning Date',default= UTC.localize(utc_time, is_dst=None).astimezone(tz).date())
    fine_amt = fields.Float('Fine Amount')
    warning_attach_id = fields.One2many('warning.attachment','attachment_id')
    attachment = fields.Binary(string='Attachment')
    attached_filename = fields.Char("Attachment Filename")
    
    @api.onchange('warning_type_id')
    def onchange_warning_type_id(self):
        if self.warning_type_id:
            self.warning_title_id = self.warning_type_id.warning_title_ids and self.warning_type_id.warning_title_ids[0] or False
            self.mark = self.warning_type_id.mark
            temp_lines = self.env['hr.warning.temp']
            if self.warning_type_id.manager_mark != 0 and self.employee_id.parent_id.id:
                temp_lines += temp_lines.new({'employee_id': self.employee_id.parent_id.id, 'mark': self.warning_type_id.manager_mark})
            if self.employee_id.parent_id != self.employee_id.approve_manager and self.warning_type_id.approval_mark != 0 and self.employee_id.approve_manager.id:
                temp_lines += temp_lines.new({'employee_id': self.employee_id.approve_manager.id, 'mark': self.warning_type_id.approval_mark})
            if self.employee_id.approve_manager != self.employee_id.dotted_line_manager_id and self.warning_type_id.dotted_line_mark != 0 and self.employee_id.dotted_line_manager_id.id:
                temp_lines += temp_lines.new({'employee_id': self.employee_id.dotted_line_manager_id.id, 'mark': self.warning_type_id.dotted_line_mark})
            self.temp_lines = temp_lines
    
    def action_submit(self):
        self.state = 'submit'

    def action_approve(self):
        for temp in self.temp_lines:
            today = fields.Date.today()
            today_plus_one = today + timedelta(days=1)
            fiscal_year = self.env['account.fiscal.year'].sudo().search([('date_from', '<=', today_plus_one), 
                                                                        ('date_to', '>=', today_plus_one), 
                                                                        ('company_id', '=', temp.employee_id.company_id.id)], limit=1)
            self.create({
                'employee_id': temp.employee_id.id,
                'company_id': temp.employee_id.company_id.id,
                'branch_id': temp.employee_id.branch_id.id,
                'department_id': temp.employee_id.department_id.id,
                'date': self.date,
                'warn_date': self.warn_date,
                'description': self.description,
                'warning_type_id': self.warning_type_id.id,
                'warning_title_id': self.warning_title_id.id,
                'linked_warning_id': self.id,
                'mark': temp.mark,
                'fine_amt': self.fine_amt,
                'fiscal_year': fiscal_year.id,
                'approved': True,
            })
        self.temp_lines.unlink()
        self.approved = True
        self.state = 'approve'
        self.manager_warning_ids.write({'state': 'approve'})
        one_signal_values = {'employee_id': self.employee_id.id,
                            'contents': _('%s is Warning for %s') % (self.employee_id.name, self.warning_title_id.name),
                            'headings': _('WB B2B : Warning CREATED')}
        self.env['one.signal.notification.message'].create(one_signal_values)

    def action_decline(self):
        self.state = 'decline'
                    
    @api.model
    def create(self, vals):
        warning_no = self.env['ir.sequence'].next_by_code('warning.code')
        if warning_no:                          
            vals['name'] = warning_no
        return super(HRWarning, self).create(vals)
    
    def create_temp_lines(self):
        temp_lines = self.env['hr.warning.temp']
        if self.warning_type_id.manager_mark != 0 and self.employee_id.parent_id.id:
            temp_lines += temp_lines.new({'employee_id': self.employee_id.parent_id.id, 'mark': (self.warning_type_id.manager_mark * 0.5)})
        if self.employee_id.parent_id != self.employee_id.approve_manager and self.warning_type_id.approval_mark != 0 and self.employee_id.approve_manager.id:
            temp_lines += temp_lines.new({'employee_id': self.employee_id.approve_manager.id, 'mark': (self.warning_type_id.approval_mark * 0.5)})
        if self.employee_id.approve_manager != self.employee_id.dotted_line_manager_id and self.warning_type_id.dotted_line_mark != 0 and self.employee_id.dotted_line_manager_id.id:
            temp_lines += temp_lines.new({'employee_id': self.employee_id.dotted_line_manager_id.id, 'mark': (self.warning_type_id.dotted_line_mark * 0.5)})
        self.temp_lines = temp_lines

    def _generate_warning_carried_forward(self, employee_ids=None):
        today = fields.Date.today()
        prev_month = today - timedelta(days=30)
        today_plus_one = today + timedelta(days=1)
        fiscal_obj = self.env['account.fiscal.year'].sudo()
        fiscal_year = fiscal_obj.search([('date_from', '<=', prev_month), 
                                        ('date_to', '>=', prev_month)], limit=1)
#         if fiscal_year and today == fiscal_year.date_to:
        warning_obj = self.env['hr.warning'].sudo()
        warning_type_obj = self.env['warning.type'].sudo()
        
        # Change prev fiscal year old warnings to expired state
        domain = [('state', '=', 'approve'), ('date', '>=', fiscal_year.date_from), ('date', '<=', fiscal_year.date_to)]
        if employee_ids:
            employees = self.env['hr.employee'].sudo().search([('id', 'in', employee_ids)])
            domain += [('employee_id', 'in', employees.ids)]
        
        prev_warnigs = warning_obj.search(domain)
        for warning in prev_warnigs:
            prev_fiscal_year = fiscal_obj.search([('date_from', '<=', prev_month), 
                                                ('date_to', '>=', prev_month), 
                                                ('company_id', '=', warning.employee_id.company_id.id)], limit=1)
            warning.state = 'expire'
            warning.approved = False
            warning.fiscal_year = prev_fiscal_year

        for warning in prev_warnigs.filtered(lambda x: not x.linked_warning_id and x.mark != 0):
            upcoming_fiscal_year = fiscal_obj.search([('date_from', '<=', today_plus_one), 
                                                    ('date_to', '>=', today_plus_one), 
                                                    ('company_id', '=', warning.employee_id.company_id.id)], limit=1)
            carry_mark = warning.mark * 0.5
            type_domain = [('name', 'ilike', warning.warning_type_id.name), ('carry_warning', '=', True)]
            warning_type_id = self.env['warning.type']
            if not warning_type_obj.search(type_domain):
                name = str(warning.warning_type_id.name) + ' Carried Forward'
                vals = {
                    'name': name,
                    'mark': warning.warning_type_id.mark,
                    'manager_mark': warning.warning_type_id.manager_mark,
                    'approval_mark': warning.warning_type_id.approval_mark,
                    'dotted_line_mark': warning.warning_type_id.dotted_line_mark,
                    'warning_title_ids': warning.warning_type_id.warning_title_ids.ids,
                    'carry_warning': True
                }
                warning_type_id = warning_type_obj.create(vals)
            else:
                warning_type_id = warning_type_obj.search(type_domain, limit=1)
            # existing_warning = warning_obj.search([
            #     ('employee_id', '=', warning.employee_id.id), 
            #     ('state', '=', 'approve'), 
            #     ('fiscal_year', '=', upcoming_fiscal_year.id),
            #     ('warning_type_id', '=', warning_type_id.id),
            #     ('warning_title_id', '=', warning.warning_title_id.id)
            # ])
            # if existing_warning:
            #     existing_warning.unlink()
            values = {
                'employee_id': warning.employee_id.id,
                'date': fields.Date.today(),
                'state': 'draft',
                'description': warning.description,
                'warning_type_id': warning_type_id.id,
                'warning_title_id': warning.warning_title_id.id,
                'mark': carry_mark,
                'fiscal_year': upcoming_fiscal_year.id,
            }
            carry_warning = warning_obj.create(values)
            if carry_warning:
                carry_warning.create_temp_lines()
                carry_warning.action_submit()
                carry_warning.action_approve()


class HrWarningTemp(models.Model):
    _name = 'hr.warning.temp'
    _description = 'Warning Temp'

    warning_id = fields.Many2one('hr.warning', required=True, ondelete="cascade")
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    mark = fields.Float('Mark', required=True)


class HrWarningAttachment(models.Model):
    _name = 'warning.attachment'

    attachment_id = fields.Many2one('hr.warning')
    attachment = fields.Binary(string='Attachment')
    attached_filename = fields.Char("Attachment Filename")
