# -*- coding: utf-8 -*-
import datetime
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

date_format = "%Y-%m-%d"
RESIGNATION_TYPE = [('resigned', 'Normal Resignation'),
                    ('fired', 'Fired by the company')]


class HrResignation(models.Model):
    _name = 'hr.resignation'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string="Employee", default=lambda self: self.env.user.employee_id.id,
                                  help='Name of the employee for whom the request is creating')
    company_id = fields.Many2one('res.company', string='Company', related='employee_id.company_id')
    branch_id = fields.Many2one('res.branch', string='Branch', related='employee_id.branch_id')
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    help='Department of the employee')
    resign_confirm_date = fields.Date(string="Confirmed Date",
                                      help='Date on which the request is confirmed by the employee.',
                                      track_visibility="always")
    approved_revealing_date = fields.Date(string="Approved Last Day Of Employee", required=True,
                                          help='Date on which the request is confirmed by the manager.',
                                          track_visibility="always")
    joined_date = fields.Date(string="Join Date", required=False, readonly=True, related="employee_id.joining_date",
                              help='Joining date of the employee.i.e Start date of the first contract')

    expected_revealing_date = fields.Date(string="Last Day of Employee",
                                          help='Employee requested date on which he is revealing from the company.')
    reason = fields.Many2one('hr.reasons')
    notice_period = fields.Char(string="Notice Period")
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('approved', 'Approved'), ('cancel', 'Rejected')],
        string='Status', default='draft', track_visibility="always")
    resignation_type = fields.Selection(selection=RESIGNATION_TYPE, help="Select the type of resignation: normal "
                                                                         "resignation or fired by the company")
    read_only = fields.Boolean(string="check field")
    employee_contract = fields.Char(String="Contract")
    new_approved_manager_id = fields.Many2one('hr.employee', string='New Approved Manager')

    @api.onchange('employee_id')
    @api.depends('employee_id')
    def _compute_read_only(self):
        """ Use this function to check weather the user has the permission to change the employee"""
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        print(res_user.has_group('hr.group_hr_user'))
        if res_user.has_group('hr.group_hr_user'):
            self.read_only = True
        else:
            self.read_only = False

    # @api.onchange('employee_id')
    # def set_join_date(self):
    #     self.joined_date = self.employee_id.joining_date if self.employee_id.joining_date else ''

    @api.model
    def create(self, vals):
        # assigning the sequence for the record
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.resignation') or _('New')
        return super(HrResignation, self).create(vals)

    @api.constrains('employee_id')
    def check_employee(self):
        # Checking whether duplicate record of same employee
        for rec in self:
            if rec.employee_id:
                duplicate_resignations = self.search([('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id)])
                if duplicate_resignations:
                    raise ValidationError(_('You cannot create another request for the same employee.'))

    @api.onchange('employee_id')
    @api.depends('employee_id')
    def check_request_existence(self):
        # Check whether any resignation request already exists
        for rec in self:
            if rec.employee_id:
                resignation_request = self.env['hr.resignation'].search([('employee_id', '=', rec.employee_id.id),
                                                                         ('state', 'in', ['confirm', 'approved'])])
                if resignation_request:
                    raise ValidationError(_('There is a resignation request in confirmed or'
                                            ' approved state for this employee'))
                if rec.employee_id:
                    no_of_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
                    for contracts in no_of_contract:
                        if contracts.state == 'open':
                            rec.employee_contract = contracts.name
                            rec.notice_period = contracts.notice_days

    @api.constrains('joined_date')
    def _check_dates(self):
        # validating the entered dates
        for rec in self:
            resignation_request = self.env['hr.resignation'].search([('employee_id', '=', rec.employee_id.id),
                                                                     ('state', 'in', ['confirm', 'approved'])])
            if resignation_request:
                raise ValidationError(_('There is a resignation request in confirmed or approved state for this employee'))

    def check_benefit_handover(self):
        if self.employee_id:
            benefit = self.env['employee.job.benefit.line'].search([('emp_benefit_id', '=', self.employee_id.id), ('state', '=', 'on_hand')])
            if len(benefit) > 0:
                raise ValidationError(_('Please make first hand over employee benefit'))

    def check_loan_paid(self):
        if self.employee_id:
            loan_line = self.env['hr.loan.line'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'open')])
            if loan_line:
                raise ValidationError(_('Please make clear Loan first.'))
        
    def confirm_resignation(self):
        self.check_benefit_handover()
        self.check_loan_paid()
        if self.joined_date:
            if self.joined_date and self.approved_revealing_date and self.joined_date >= self.approved_revealing_date:
                raise ValidationError(_('Last date of the Employee must be anterior to Joining date'))
            for rec in self:
                rec.state = 'confirm'
                rec.resign_confirm_date = str(datetime.now())
            if self.employee_id.branch_id.manager_id:
                one_signal_values = {'employee_id': self.employee_id.branch_id.manager_id.id,
                                    'contents': _('RESIGNATION : To Approve Resignation %s.') % (self.name),
                                    'headings': _('WB B2B : APPROVAL RESIGNATION')}
                self.env['one.signal.notification.message'].create(one_signal_values)
        else:
            raise ValidationError(_('Please set joining date for employee'))

    def cancel_resignation(self):
        for rec in self:
            rec.state = 'cancel'

    def reject_resignation(self):
        for rec in self:
            rec.state = 'cancel'

    def reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.employee_id.active = True
            rec.employee_id.resigned = False
            rec.employee_id.fired = False

    def approve_resignation(self):
        for rec in self:
            if rec.approved_revealing_date and rec.resign_confirm_date:
                no_of_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
                for contracts in no_of_contract:
                    if contracts.state == 'open':
                        rec.employee_contract = contracts.name
                        contracts.write({
                            'date_end': rec.approved_revealing_date,
                            'state': 'close',
                            'active': False
                        })
                    else:
                        contracts.write({
                            'state': 'close',
                            'active': False
                        })
                rec.employee_id.resign_date = rec.approved_revealing_date
                rec.state = 'approved'
                if rec.resignation_type == 'resigned':
                    rec.employee_id.resigned = True
                    rec.employee_id.departure_reason = 'resigned'
                else:
                    rec.employee_id.fired = True
                    rec.employee_id.departure_reason = 'fired'
                rec.employee_id.departure_description = rec.reason
                if rec.approved_revealing_date <= fields.Date.today() and rec.employee_id.active:
                    #rec.employee_id.active = False
                    rec.employee_id.toggle_active()

                    for approve in self.env['hr.employee'].sudo().search([('approve_manager','=',rec.employee_id.id)]):
                        approve.write({'approve_manager': False})
                        if rec.new_approved_manager_id:
                            approve.write({'approve_manager':rec.new_approved_manager_id.id})
                    if rec.employee_id.id == rec.department_id.manager_id.id:
                        rec.department_id.write({'manager_id':False})
                    if rec.employee_id.user_id:
                        rec.employee_id.user_id.active = False
                        rec.employee_id.user_id = None
            else:
                raise ValidationError(_('Please enter valid dates.'))

    def update_employee_status(self):
        resignation = self.env['hr.resignation'].search([('state', '=', 'approved')])
        for rec in resignation:
            if rec.approved_revealing_date == fields.Date.today() and rec.employee_id.active:
                #rec.employee_id.active = False
                rec.employee_id.toggle_active()
                # Changing fields in the employee table with respect to resignation
                rec.employee_id.resign_date = rec.approved_revealing_date
                for approve in self.env['hr.employee'].sudo().search([('approve_manager', '=', rec.employee_id.id)]):
                    approve.write({'approve_manager': False})
                    if rec.new_approved_manager_id:
                        approve.write({'approve_manager': rec.new_approved_manager_id.id})
                if rec.employee_id.id == rec.department_id.manager_id.id:
                    rec.department_id.write({'manager_id': False})

                if rec.resignation_type == 'resigned':
                    rec.employee_id.resigned = True
                else:
                    rec.employee_id.fired = True
                # Removing and deactivating user
                if rec.employee_id.user_id:
                    rec.employee_id.user_id.active = False
                    rec.employee_id.user_id = None


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    resign_date = fields.Date('Resign Date', readonly=True, help="Date of the resignation")
    resigned = fields.Boolean(string="Resigned", default=False, store=True,
                              help="If checked then employee has resigned")
    fired = fields.Boolean(string="Fired", default=False, store=True, help="If checked then employee has fired")


class HrReason(models.Model):
    _name = 'hr.reasons'

    name = fields.Char('Reason Name')

