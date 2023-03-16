from odoo import fields, models, api, _
from datetime import timedelta, datetime, date, time
from pytz import timezone, UTC
from odoo.tools import float_compare, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
from odoo.exceptions import UserError, ValidationError
import math
from dateutil.relativedelta import relativedelta


def float_to_time(value):
    if value < 0:
        value = abs(value)

    hour = int(value)
    minute = round((value % 1) * 60)

    if minute == 60:
        minute = 0
        hour = hour + 1
    return time(hour, minute)

def get_utc_datetime_mobile(tz, local_dt_str):
    local_datetime = datetime.strptime(local_dt_str, DT_FORMAT)
    utc_datetime = tz.localize(local_datetime.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
    return utc_datetime.strftime(DT_FORMAT)

def get_utc_datetime(tz, local_datetime):
    return tz.localize(local_datetime.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)


def get_local_datetime(tz, utc_datetime):
    return UTC.localize(utc_datetime.replace(tzinfo=None), is_dst=True).astimezone(tz=tz)


class TravelRequest(models.Model):
    _name = 'travel.request'
    _description = 'Travel Request'
    _order = 'id desc'

    name = fields.Char('Name', default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    start_date = fields.Date(string='Start Date', required=True, copy=False,context="{'readonly_by_pass': True}")
    end_date = fields.Date(string='End Date', required=True, copy=False)
    duration = fields.Float(string='Duration (days)', compute='compute_duration')
    attachment = fields.Binary(string="Attachment")
    city_from = fields.Char(string='From')
    city_to = fields.Char(string='To')
    travel_line = fields.One2many('travel.request.line', 'request_id', string='Travel')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('advance_request', 'Advance Requested'),
        ('advance_withdraw', 'Advance Withdrew'),
        ('in_progress', 'In Progress'),
        ('cancel', 'Declined'),
        ('done', 'Done'),
        ('verify', 'Verified'),
        ('cancelled','Cancel'),
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    travel_type_id = fields.Many2one('hr.travel.type', string='Travel Type')
    request_allowance_lines = fields.One2many('travel.request.allowance', 'request_id', string='Allowance Lines')
    total_advance = fields.Float('Advanced Total', compute='_compute_total_advance')
#     standard_allowance_total = fields.Float('Standard Allowance Total', compute='_compute_allowance_amount')
#     actual_allowance_total = fields.Float('Actual Allowance Total', compute='_compute_allowance_amount')
#     total_difference = fields.Float('Difference', compute='_compute_allowance_amount')
    payment_id = fields.Many2one('account.payment', string='Payment')
    enable_approval = fields.Boolean('Enable Approval')
    payment_amount = fields.Float(compute='_compute_payment_amount', string='Payment Amount', readonly=True, store=True)
    is_required = fields.Boolean(string='Is Required?', compute='compute_is_required')
    remark = fields.Text(string='Remark')
    origin_start_date = fields.Date(string='Origin Start Date')

    @api.depends('end_date')
    def compute_is_required(self):
        for rec in self:
            if rec.state != 'draft' and rec.end_date != rec._origin.end_date:
                rec.is_required = True
            else:
                rec.is_required = False

    @api.depends('payment_id')
    def _compute_payment_amount(self):
        for data in self:
            if data.payment_id:      
                data.update({                
                    'payment_amount': data.payment_id.amount,
                })
            else:
                data.update({                
                    'payment_amount': 0,
                })
    
    @api.depends('travel_line.full', 'travel_line.first', 'travel_line.second')
    def compute_duration(self):
        for day in self:
            total_day = 0
            for line in day.travel_line:
                total_day += 1 if line.full else 0.5
            day.duration = total_day

    # @api.depends('employee_id')
    # @api.depends_context('employee_id')
    # def _compute_enable_approval(self):
    #     for req in self:
    #         if self.env.context.get('employee_id'):
    #             domain = [('id', '=', self.env.context.get('employee_id'))]
    #         else:
    #             domain = [('user_id', '=', self.env.user.id)]
    #         employee = self.env['hr.employee'].search(domain, limit=1)
    #         # if employee and req.employee_id.branch_id and req.employee_id.branch_id.manager_id == employee or employee.is_branch_manager and req.employee_id == employee:
    #         if employee and req.employee_id.branch_id and req.employee_id.branch_id.manager_id == employee:
    #             req.enable_approval = True
    #         else:
    #             req.enable_approval = False

    def _create_approval_notification_message(self, employee=None):
        if employee:
            one_signal_values = {'employee_id': employee.id,
                                 'contents': _('TRAVEL REQUEST : %s submitted travel request.') % self.employee_id.name,
                                 'headings': _('WB B2B : SUBMITTED TRAVEL REQUEST')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def _create_approved_notification_message(self, employee=None):
        if employee:
            one_signal_values = {'employee_id': employee.id,
                                 'contents': _('TRAVEL REQUEST : %s approved travel request.') % employee.branch_id.manager_id.name,
                                 'headings': _('WB B2B : APPROVED TRAVEL REQUEST')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def _validate_leaves(self):
        for line in self.travel_line:
            domain = [('date_from', '<', line.end_date), ('date_to', '>', line.start_date),
                      ('employee_id', '=', self.employee_id.id), ('state', 'not in', ('cancel', 'refuse'))]
            if self.env['hr.leave'].search(domain):
                return {'status': False, 'message': 'You can not set 2 times off that overlaps on the same day for the same employee.'}
        return {'status': True, 'message': 'Successfully Submitted!'}

    def action_submit(self):
        result = self._validate_leaves()
        if not result['status']:
            raise ValidationError(result['message'])
        self.state = 'submit'
        if self.employee_id.branch_id and self.employee_id.branch_id.manager_id:
            self._create_approval_notification_message(self.employee_id.branch_id.manager_id)

    def button_submit(self):
        result = self._validate_leaves()
        if result['status']:
            self.state = 'submit'
            if self.employee_id.branch_id and self.employee_id.branch_id.manager_id:
                self._create_approval_notification_message(self.employee_id.branch_id.manager_id)
        return result

    def button_approve(self):
        leave_type = self.env['hr.leave.type'].search([('travel_leave', '=', True)])
        if leave_type:
            resource_calendar = self.employee_id.contract_id and self.employee_id.contract_id.resource_calendar_id or self.employee_id.resource_calendar_id
            tz = timezone(resource_calendar.tz)
            for line in self.travel_line:
                no_of_days = 1 if line.full else 0.5
                travel_leave = self.env['hr.leave'].create({'employee_id': self.employee_id.id,
                                                            'date_from': line.start_date,
                                                            'date_to': line.end_date,
                                                            'holiday_status_id': leave_type.id,
                                                            'request_date_from': get_local_datetime(tz, line.start_date).date(),
                                                            'request_date_to': get_local_datetime(tz, line.end_date).date(),
                                                            'number_of_days': no_of_days,
                                                            'travel_request_id': self.id,
                                                            'state':'draft',
                                                            })
#                 travel_leave.action_approve()
#                 travel_leave.action_validate()
                travel_leave.action_confirm()
                travel_leave.action_approve()
#             if self.travel_type_id and self.employee_id.address_home_id and self.actual_allowance_total:
#                 company = self.employee_id.company_id
#                 journal = self.env['account.journal'].search([('type', 'in', ('bank', 'cash')), ('company_id', '=', company.id)], limit=1)
#                 payment_value = {'payment_type': 'outbound',
#                                  'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
#                                  'partner_type': 'customer',
#                                  'partner_id': self.employee_id.address_home_id.id,
#                                  'amount': self.actual_allowance_total,
#                                  'currency_id': company.currency_id.id,
#                                  'payment_date': fields.Date.today(),
#                                  'journal_id': journal.id,
#                                  'communication': self.name,
#                                  'payment_reference': self.name,
#                                  }
#                 payment = self.env['account.payment'].create(payment_value)
#                 if payment:
#                     self.payment_id = payment.id
                    
            self.state = 'approve'
            self._create_approved_notification_message(self.employee_id)
            # if self.employee_id.approve_manager:
            #     self._create_approved_notification_message(self.employee_id.approve_manager)

    def button_cancel(self):
        self.state = 'cancel'
        for leave in self.env['hr.leave'].search([('travel_request_id', '=', self.id),('state','in',('draft', 'confirm', 'validate', 'validate1'))]):
            leave.action_refuse()
        one_signal_values = {'employee_id': self.employee_id.id,
                             'contents': _('TRAVEL REQUEST : rejected travel request.'),
                             'headings': _('WB B2B : REJECTED TRAVEL REQUEST')}
        self.env['one.signal.notification.message'].create(one_signal_values)

    def button_draft(self):
        self.state = 'draft'

    def button_cancelled(self):
        self.state = 'cancelled'

    def button_verify(self):
        self.state = 'verify'
    #revert code temporary  
    def button_request_balance(self):
        previous_requests = self.env['travel.request'].sudo().search([('employee_id', '=', self.employee_id.id), 
                                                                    ('id', '!=', self.id)])
        previous_expenses = self.env['hr.travel.expense']
        if previous_requests:
            previous_expenses = previous_expenses.sudo().search([('travel_id', 'in', previous_requests.ids), 
                                                                ('state', 'in', ('draft', 'submit', 'approve', 'reject'))])
        if previous_requests and previous_expenses:
            raise ValidationError(_('Please settle former advance expense first.'))
        else:
            journal = self.env['account.journal'].search([('company_id', '=', self.employee_id.company_id.id),('type', '=', 'bank')], limit=1)
            if journal:
                bank_journal = journal.id
            method = self.env['account.payment.method'].search([('payment_type', '=', 'outbound')], limit=1)
            if method:
                payment_method = method.id
            #outbound
            values = {
                        'payment_type': 'outbound',
                        'partner_type': 'customer',
                        'partner_id': self.employee_id.address_home_id.id,
                        'company_id': self.employee_id.company_id.id,
                        'amount': self.total_advance,
                        'payment_date': fields.Date.today(),
                        'communication': 'Advance money',
                        'journal_id': bank_journal,
                        'travel_request_id': self.id,
                        'payment_method_id': payment_method,
                    }
            payment = self.env['account.payment'].sudo().create(values)
            if payment:
                self.payment_id = payment.id
            if self.request_allowance_lines:
                total_amount = 0
                for line in self.request_allowance_lines:
                    total_amount +=line.amount
                if not total_amount:
                    self.state='advance_withdraw'
                else:
                    self.state = 'advance_request'
    
#     def button_request_balance(self):
#         journal = self.env['account.journal'].search([('company_id', '=', self.employee_id.company_id.id),('type', '=', 'bank')], limit=1)
#         if journal:
#             bank_journal = journal.id
#         method = self.env['account.payment.method'].search([('payment_type', '=', 'outbound')], limit=1)
#         if method:
#             payment_method = method.id
#         #outbound
#         values = {
#                     'payment_type': 'outbound',
#                     'partner_type': 'customer',
#                     'partner_id': self.employee_id.address_home_id.id,
#                     'company_id': self.employee_id.company_id.id,
#                     'amount': self.total_advance,
#                     'payment_date': fields.Date.today(),
#                     'communication': 'Advance money',
#                     'journal_id': bank_journal,
#                     'travel_request_id': self.id,
#                     'payment_method_id': payment_method,
#                 }
#         payment = self.env['account.payment'].sudo().create(values)
#         if payment:
#            self.payment_id = payment.id
#             
#         self.state = 'advance_request'


    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        # import pdb
        # pdb.set_trace()
        if self.state=='draft':
            self.update({'origin_start_date':self.start_date})
        forward_date =self.origin_start_date+timedelta(days=3)
        backward_date = self.origin_start_date-timedelta(days=3)
        if not (self.start_date<=forward_date and self.start_date>=backward_date):
            raise ValidationError(_('Start Date should be between %s and %s')%(backward_date,forward_date))

        if self.start_date > self.end_date:
            raise ValidationError(_('End Date should be greater than or equal to Start Date.'))
       
    @api.onchange('start_date', 'end_date', 'employee_id')
    def onchange_dates(self):
        if self.start_date and self.end_date and self.employee_id:
            
            resource_calendar_id = self.employee_id.contract_id and self.employee_id.contract_id.resource_calendar_id or self.employee_id.resource_calendar_id
            day_count = (self.end_date - self.start_date).days + 1
            travel_lines = self.env['travel.request.line']
            for single_date in (self.start_date + timedelta(n) for n in range(day_count)):
                new_line_values = travel_lines.calculate_line_values(resource_calendar_id, single_date)
                for new_line_value in new_line_values:
                    distinct_shift = new_line_value['distinct_shift']
                    next_day_hour_id = new_line_value['next_day_hour_id']
                    this_day_hour_id = new_line_value['this_day_hour_id']
                    new_line_value.update(travel_lines._compute_allow_edit(single_date, self.start_date, self.end_date, this_day_hour_id, next_day_hour_id, distinct_shift))
                    if self.city_to:
                        destination = self.city_from + ' - ' + self.city_to if self.city_from else self.city_to
                        new_line_value.update({'destination': destination})
                    new_line = travel_lines.new(new_line_value)
                    travel_lines += new_line
            self.travel_line = travel_lines
#             contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'open')], limit=1)
#             if contract:
#                 if contract.job_grade_id:
#                     travel_type = self.env['hr.travel.type'].search([('job_grade_id', '=', contract.job_grade_id.id)], limit=1)
#                     if travel_type:
#                         self.travel_type_id = travel_type.id
                        
    @api.onchange('city_from', 'city_to')
    def onchange_cities(self):
        if self.city_from and self.city_to:
            for line in self.travel_line:
                line.destination = self.city_from + ' - ' + self.city_to

#     @api.onchange('travel_type_id')
#     def onchange_travel_type_id(self):
#         if self.travel_type_id:
#             allowance_lines = self.env['travel.request.allowance']
#             for allowance in self.travel_type_id.allowance_ids:
#                 new_line_value = {'travel_allowance_id': allowance.id,
#                                   'remark': allowance.remark}
#                 new_line = allowance_lines.new(new_line_value)
#                 allowance_lines += new_line
#             self.request_allowance_lines = allowance_lines

#     @api.depends('request_allowance_lines.standard_amount', 'request_allowance_lines.actual_amount')
#     def _compute_allowance_amount(self):
#         for request in self:
#             standard_allowance_total = actual_allowance_total = 0
#             for allowance in request.request_allowance_lines:
#                 standard_allowance_total += allowance.standard_amount
#                 actual_allowance_total += allowance.actual_amount
#             request.standard_allowance_total = standard_allowance_total
#             request.actual_allowance_total = actual_allowance_total
#             request.total_difference = standard_allowance_total - actual_allowance_total

    @api.depends('request_allowance_lines.total_amount')
    def _compute_total_advance(self):
        for request in self:
            total_advance = 0
            for allowance in request.request_allowance_lines:
                total_advance += allowance.total_amount
            request.total_advance = total_advance

    @api.model
    def create(self, vals):
        SequenceObj = self.env['ir.sequence']
        seq_no = SequenceObj.next_by_code('travel.request')
        vals['name'] = seq_no
        
        res = super(TravelRequest, self).create(vals)
        tz = timezone('Asia/Yangon')
        
        if not self._context.get('from_web_view'):
            
            travel = self.browse(res.id)
            for line in travel.travel_line:
                start_date = line.start_date - relativedelta(hours=6, minutes=30)
                end_date = line.end_date - relativedelta(hours=6, minutes=30)
                line.write({'start_date':start_date,'end_date':end_date})        
        return res

    @api.constrains('start_date', 'end_date', 'employee_id')
    def check_overlap_record(self):
        for req in self:
            if req.start_date and req.end_date and req.employee_id:
                result = req._validate_leaves()
                if not result['status']:
                    raise ValidationError(result['message'])


class TravelLine(models.Model):
    _name = 'travel.request.line'

    request_id = fields.Many2one('travel.request', string='Travel Request', index=True, required=True,
                                 ondelete='cascade')
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', required=True, index=True, default='0')
    date = fields.Date(string='Date')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    destination = fields.Char(string='Destination')
    purpose = fields.Char(string='Purpose', required=True)
    full = fields.Boolean(string='Full', default=True)
    first = fields.Boolean(string='First Half', default=False)
    second = fields.Boolean(string='Second Half', default=False)
    resource_calendar_id = fields.Many2one('resource.calendar')
    this_day_hour_id = fields.Many2one('resource.calendar.attendance', string='This Day')
    next_day_hour_id = fields.Many2one('resource.calendar.attendance', string='Next Day')
    distinct_shift = fields.Selection([('whole', 'The Whole Day'), ('morning', 'Morning '), ('afternoon', 'Afternoon')], default='', copy=False)
    allow_full_edit = fields.Boolean('Allow Editing')
    allow_first_edit = fields.Boolean('Allow Editing')
    allow_second_edit = fields.Boolean('Allow Editing')

    def _compute_allow_edit(self, request_date, start_date, end_date, this_day_hour_id, next_day_hour_id, distinct_shift=''):
        if not this_day_hour_id and not next_day_hour_id:
            if request_date == start_date:
                return {'allow_full_edit': True, 'allow_first_edit': False, 'allow_second_edit': True}
            elif request_date == end_date:
                return {'allow_full_edit': True, 'allow_first_edit': True, 'allow_second_edit': False}
            else:
                return {'allow_full_edit': False, 'allow_first_edit': False, 'allow_second_edit': False}

        allow_full_edit = True
        allow_first_edit = True
        allow_second_edit = True
        if distinct_shift == 'afternoon':
            allow_first_edit = False
            allow_full_edit = False
        elif distinct_shift == 'morning':
            allow_second_edit = False
            allow_full_edit = False

        if start_date == end_date:
            if next_day_hour_id or distinct_shift == 'morning':
                allow_second_edit = False
            else:
                allow_second_edit = True
        elif request_date == start_date:
            allow_first_edit = False
        elif request_date == end_date:
            allow_second_edit = False
        else:
            allow_full_edit = False
            allow_first_edit = False
            allow_second_edit = False
        return {'allow_full_edit': allow_full_edit, 'allow_first_edit': allow_first_edit, 'allow_second_edit': allow_second_edit}

    def _get_domain(self, resource_calendar, date):
        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', resource_calendar.id),
                  ('dayofweek', '=', str(date.weekday()))]
        if resource_calendar.two_weeks_calendar:
            week_type = int(math.floor((date.toordinal() - 1) / 7) % 2)
            domain += [('week_type', '=', str(week_type))]
        return domain

    def calculate_line_values(self, resource_calendar, date):
        value_lines = []
        calendar_obj = self.env['resource.calendar.attendance']
        dayofweek = str(date.weekday())
        tz = timezone(resource_calendar.tz)
        domain = self._get_domain(resource_calendar, date)
        working_hours = calendar_obj.search(domain)
        if not working_hours:
            local_start_date = datetime.combine(fields.Datetime.to_datetime(date), float_to_time(9.0))
            local_end_date = datetime.combine(fields.Datetime.to_datetime(date), float_to_time(17.5))
            start_date = datetime.strftime(get_utc_datetime(tz, local_start_date), DT_FORMAT)
            end_date = datetime.strftime(get_utc_datetime(tz, local_end_date), DT_FORMAT)
            value_lines.append({'dayofweek': dayofweek,
                                'date': date,
                                'start_date': start_date,
                                'end_date': end_date,
                                'distinct_shift': 'whole',
                                'full': True,
                                'first': False,
                                'second': False,
                                'this_day_hour_id': 0,
                                'next_day_hour_id': 0,
                                'resource_calendar_id': resource_calendar.id})

        for hour in working_hours:
            if round(hour.hour_from) == 0:
                continue
            elif round(hour.hour_to) == 24:
                local_start_date = datetime.combine(fields.Datetime.to_datetime(date), float_to_time(hour.hour_from))

                next_date = date + timedelta(days=1)
                next_domain = self._get_domain(resource_calendar, next_date)
                next_hour = calendar_obj.search(next_domain).filtered(lambda h: round(h.hour_from) == 0)

                local_end_date = datetime.combine(fields.Datetime.to_datetime(next_date), float_to_time(next_hour.hour_to))

                start_date = datetime.strftime(get_utc_datetime(tz, local_start_date), DT_FORMAT)
                end_date = datetime.strftime(get_utc_datetime(tz, local_end_date), DT_FORMAT)
                value_lines.append({'dayofweek': dayofweek,
                                    'date': date,
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'distinct_shift': '',
                                    'full': True,
                                    'first': False,
                                    'second': False,
                                    'this_day_hour_id': hour.id,
                                    'next_day_hour_id': next_hour.id,
                                    'resource_calendar_id': resource_calendar.id,
                                    })
            else:
                local_start_date = datetime.combine(fields.Datetime.to_datetime(date), float_to_time(hour.hour_from))
                local_end_date = datetime.combine(fields.Datetime.to_datetime(date), float_to_time(hour.hour_to))
                start_date = datetime.strftime(get_utc_datetime(tz, local_start_date), DT_FORMAT)
                end_date = datetime.strftime(get_utc_datetime(tz, local_end_date), DT_FORMAT)
                value = {'dayofweek': dayofweek,
                         'date': date,
                         'start_date': start_date,
                         'end_date': end_date,
                         'this_day_hour_id': hour.id,
                         'next_day_hour_id': 0,
                         'resource_calendar_id': resource_calendar.id}
                if working_hours.filtered(lambda h: round(h.hour_from) == 0):
                    value.update({'distinct_shift': 'afternoon', 'second': True, 'first': False, 'full': False})
                elif working_hours.filtered(lambda h: round(h.hour_to) == 24):
                    value.update({'distinct_shift': 'morning', 'first': True, 'second': False, 'full': False})
                else:
                    value.update({'distinct_shift': 'whole', 'full': True, 'second': False, 'first': False})
                value_lines.append(value)
        return value_lines

    @api.onchange('full', 'first', 'second')
    def onchange_leave_options(self):
        if self.resource_calendar_id:
            start_date, end_date = self.manipulate_options(self.date, self.this_day_hour_id.id, self.next_day_hour_id.id, self.distinct_shift, self.first, self.second)
            self.start_date = datetime.strftime(start_date, DT_FORMAT)
            self.end_date = datetime.strftime(end_date, DT_FORMAT)

    def manipulate_options(self, request_date, this_day_hour_id, next_day_hour_id, distinct_shift, first, second):
        rca_obj = self.env['resource.calendar.attendance']
        this_day_hour = rca_obj.browse(this_day_hour_id) if this_day_hour_id else False
        next_day_hour = rca_obj.browse(next_day_hour_id) if next_day_hour_id else False
        from_date = to_date = request_date
        next_day = request_date + timedelta(days=1)
        tz = timezone(self.resource_calendar_id.tz or 'Asia/Yangon')

        if not this_day_hour_id and not next_day_hour_id:
            if first:
                hour_from = 9.0
                hour_to = 13.25
            elif second:
                hour_from = 13.25
                hour_to = 17.5
            else:
                hour_from = 9.0
                hour_to = 17.5

        elif not distinct_shift or distinct_shift == '':
            if first:
                hour_from = this_day_hour.hour_from
                hour_to = this_day_hour.hour_to
            elif second:
                hour_from = next_day_hour.hour_from
                hour_to = next_day_hour.hour_to
                from_date = to_date = next_day
            else:
                hour_from = this_day_hour.hour_from
                if next_day_hour:
                    hour_to = next_day_hour.hour_to
                    to_date = next_day
                else:
                    hour_to = this_day_hour.hour_to

        elif distinct_shift == 'whole':
            hours = this_day_hour
            half_day = (hours.hour_from + hours.hour_to) / 2
            if first:
                hour_from = hours.hour_from
                hour_to = half_day
            elif second:
                hour_from = half_day
                hour_to = hours.hour_to
            else:
                hour_from = this_day_hour.hour_from
                hour_to = this_day_hour.hour_to
        else:
            hour_from = this_day_hour.hour_from
            hour_to = this_day_hour.hour_to

        local_start_date = datetime.combine(fields.Datetime.to_datetime(from_date), float_to_time(hour_from))
        local_end_date = datetime.combine(fields.Datetime.to_datetime(to_date), float_to_time(hour_to))
        if self._context.get('via') and self._context.get('via') == 'mobile':
            return local_start_date, local_end_date
        start_date = get_utc_datetime(tz, local_start_date)
        end_date = get_utc_datetime(tz, local_end_date)
        return start_date, end_date


class TravelRequestAllowance(models.Model):
    _name = 'travel.request.allowance'
    _description = 'Travel Request Allowance'

    request_id = fields.Many2one('travel.request', string='Travel Request', index=True,
                                 ondelete='cascade')
    expense_categ_id = fields.Many2one('product.category', string="Expense Category")
    quantity = fields.Float('Quantity')
    amount = fields.Float('Amount')
    total_amount = fields.Float('Total Amount')
#     type_id = fields.Many2one('hr.travel.type', related='request_id.travel_type_id')
#     travel_allowance_id = fields.Many2one('hr.travel.allowance', string='Name', required=True)
#     standard_amount = fields.Float(related='travel_allowance_id.standard_amount', string='Standard Amount')
#     actual_amount = fields.Float('Actual Amount')
    remark = fields.Char('Remark')
    
    @api.onchange('quantity', 'amount')
    def onchange_quantity(self):
        self.total_amount = self.quantity * self.amount
    
    @api.onchange('quantity', 'total_amount')
    def onchange_total_amount(self):
        if self.quantity != 0:
            self.amount = self.total_amount / self.quantity

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    travel_request_id = fields.Many2one('travel.request')
