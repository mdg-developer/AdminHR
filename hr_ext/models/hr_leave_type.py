from collections import defaultdict
from datetime import datetime, date, timedelta
from pytz import timezone, UTC
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
import math
from collections import namedtuple
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')

class HrLeave(models.Model):
    _inherit = 'hr.leave'
    
    remaining_leaves = fields.Float(string='Balance (Days)', compute='_compute_remaining_leaves', store=True)
    
    @api.depends('employee_id', 'holiday_status_id.max_leaves', 'holiday_status_id.leaves_taken')
    def _compute_remaining_leaves(self):
        for leave in self:
            leave_type = leave.holiday_status_id.with_context(employee_id=leave.employee_id.id)
            print("leave type : ", leave_type)
            print("max leave : ", leave_type.max_leaves)
            print("leaves taken : ", leave_type.leaves_taken)
            leave.remaining_leaves = leave_type.max_leaves - leave_type.leaves_taken
    
    def action_validate(self):
        res = super(HrLeave, self).action_validate()
        for leave in self:
            leave_balance = leave.remaining_leaves - leave.number_of_days
            leave.write({'remaining_leaves': leave_balance}) 
        return res

    @api.onchange('request_date_from_period', 'request_hour_from', 'request_hour_to',
                  'request_date_from', 'request_date_to',
                  'employee_id')
    def _onchange_request_parameters(self):
        if not self.request_date_from:
            self.date_from = False
            return
 
        if self.request_unit_half or self.request_unit_hours:
            self.request_date_to = self.request_date_from
 
        if not self.request_date_to:
            self.date_to = False
            return
 
        resource_calendar_id = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
        domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
        attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'week_type', 'dayofweek', 'day_period'], ['week_type', 'dayofweek', 'day_period'], lazy=False)
 
        # Must be sorted by dayofweek ASC and day_period DESC
        attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period'], group['week_type']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))
 
        default_value = DummyAttendance(0, 0, 0, 'morning', False)
 
        if resource_calendar_id.two_weeks_calendar:
            # find week type of start_date
            start_week_type = int(math.floor((self.request_date_from.toordinal() - 1) / 7) % 2)
            attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == start_week_type]
            attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != start_week_type]
            # First, add days of actual week coming after date_from
            attendance_filtred = [att for att in attendance_actual_week if int(att.dayofweek) >= self.request_date_from.weekday()]
            # Second, add days of the other type of week
            attendance_filtred += list(attendance_actual_next_week)
            # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
            attendance_filtred += list(attendance_actual_week)
 
            end_week_type = int(math.floor((self.request_date_to.toordinal() - 1) / 7) % 2)
            attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == end_week_type]
            attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != end_week_type]
            attendance_filtred_reversed = list(reversed([att for att in attendance_actual_week if int(att.dayofweek) <= self.request_date_to.weekday()]))
            attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
            attendance_filtred_reversed += list(reversed(attendance_actual_week))
 
            # find first attendance coming after first_day
            attendance_from = attendance_filtred[0]
            # find last attendance coming before last_day
            attendance_to = attendance_filtred_reversed[0]
        else:
            # find first attendance coming after first_day
            attendance_from = next((att for att in attendances if int(att.dayofweek) >= self.request_date_from.weekday()), attendances[0] if attendances else default_value)
            # find last attendance coming before last_day
            attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= self.request_date_to.weekday()), attendances[-1] if attendances else default_value)
 
        if self.request_unit_half:
            if self.request_date_from_period == 'am':
                hour_from = float_to_time(attendance_from.hour_from)
                hour_to = float_to_time(attendance_from.hour_to)
            else:
                hour_from = float_to_time(attendance_to.hour_from)
                hour_to = float_to_time(attendance_to.hour_to)
        elif self.request_unit_hours:
            hour_from = float_to_time(float(self.request_hour_from))
            hour_to = float_to_time(float(self.request_hour_to))
        elif self.request_unit_custom:
            hour_from = self.date_from.time()
            hour_to = self.date_to.time()
        else:
            hour_from = float_to_time(attendance_from.hour_from)
            hour_to = float_to_time(attendance_to.hour_to)
 
        tz = self.env.user.tz if self.env.user.tz and not self.request_unit_custom else 'UTC'  # custom -> already in UTC
        self.date_from = timezone(tz).localize(datetime.combine(self.request_date_from, hour_from)).astimezone(UTC).replace(tzinfo=None)
        self.date_to = timezone(tz).localize(datetime.combine(self.request_date_to, hour_to)).astimezone(UTC).replace(tzinfo=None)
        self._onchange_leave_dates()
        domain = ['&', ('virtual_remaining_leaves', '>', 0), '|', ('allocation_type', 'in', ['fixed_allocation', 'no']),'&',('allocation_type', '=', 'fixed'), ('max_leaves', '>', '0')]
        if self.employee_id:
            contract = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id),('state','=','open')],order='id desc', limit=1)
            if contract:
                leave_types = []
                leaves = self.env['hr.leave.type'].search(domain)
                for leave in leaves:
                    leave_types.append(leave.id)
                if contract.resource_calendar_id.one_day_off == True or contract.resource_calendar_id.no_holidays == True:
                    domain = ['|', ('one_day_off','=',True), ('no_holidays','=',True)]
                    leaves = self.env['hr.leave.type'].search(domain)
                    for leave in leaves:
                        leave_types.append(leave.id)
                    return {'domain': {
                        'holiday_status_id': [('id', 'in', leave_types)]
                    }}
        
    @api.constrains('date_from', 'date_to')
    def _check_contracts(self):
        """
            A leave cannot be set across multiple contracts.
            Note: a leave can be across multiple contracts despite this constraint.
            It happens if a leave is correctly created (not accross multiple contracts) but
            contracts are later modifed/created in the middle of the leave.
        """
        for holiday in self.filtered('employee_id'):
            domain = [
                ('employee_id', '=', holiday.employee_id.id),
                ('date_start', '<=', holiday.date_to),
                '|',
                ('state', 'not in', ['draft', 'cancel', 'close']),
                '&',
                ('state', '=', 'draft'),
                ('kanban_state', '=', 'done'),
                '|',
                    ('date_end', '>=', holiday.date_from),
                    '&',
                        ('date_end', '=', False),
                        ('state', '!=', 'close')
            ]
            nbr_contracts = self.env['hr.contract'].sudo().search_count(domain)
            if nbr_contracts > 1:
                contracts = self.env['hr.contract'].sudo().search(domain)
                raise ValidationError(_('A leave cannot be set across multiple contracts.') + '\n' + ', '.join(contracts.mapped('name')))

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        mapped_days = self.mapped('holiday_status_id').get_employees_days(self.mapped('employee_id').ids)
        for holiday in self:
            if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.allocation_type == 'no':
                continue
            leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
            if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                print("state : ", self.state)
                if self.state != 'refuse':
                    raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
                                            'Please also check the time off waiting for validation.'))


class HolidaysType(models.Model):    
    _inherit = 'hr.leave.type'    
    _description = 'Leaves Form Customization'

    travel_leave = fields.Boolean(string='Travel leaves')
    show_in_mobile_app = fields.Boolean(string='Show in Mobile App')
    monthly_limit = fields.Float(string='Monthly Limit')
    one_day_off = fields.Boolean(string="One Day Off",default=False)
    no_holidays = fields.Boolean(string="No Holiday",default=False)
    max_continuous_days = fields.Integer(string="Max Continuous Days")
    pre_requested_days = fields.Integer(string="Pre Requested Days")
    
    def get_employees_leave_days(self, employee_ids):
        result = {
            employee_id: {
                leave_type.id: {
                    'max_leaves': 0,
                    'leaves_taken': 0,
                    'remaining_leaves': 0,
                    'virtual_remaining_leaves': 0,
                } for leave_type in self
            } for employee_id in employee_ids
        }

        today = fields.Date.today()
        current_fiscal_year = self.env['account.fiscal.year'].sudo().search([('date_from', '<=', today), ('date_to', '>=', today)], limit=1)
        start_date = current_fiscal_year.date_from
        end_date = current_fiscal_year.date_to

        requests = self.env['summary.request'].search([
            ('employee_id', 'in', employee_ids),
            ('holiday_status_id', 'in', self.ids),
            ('state', 'in', ('approve', 'verify')),
            ('start_date', '>=', start_date),
            ('end_date', '<=', end_date),
        ])

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids)
        ])

        for request in requests:
            status_dict = result[request.employee_id.id][request.holiday_status_id.id]
            status_dict['virtual_remaining_leaves'] -= (request.number_of_hours_display
                                                    if request.leave_type_request_unit == 'hour'
                                                    else request.duration)

            status_dict['leaves_taken'] += (request.number_of_hours_display
                                        if request.leave_type_request_unit == 'hour'
                                        else request.duration)
            status_dict['remaining_leaves'] -= (request.number_of_hours_display
                                            if request.leave_type_request_unit == 'hour'
                                            else request.duration)

        for allocation in allocations.sudo():
            status_dict = result[allocation.employee_id.id][allocation.holiday_status_id.id]
            if allocation.state == 'validate':
                # note: add only validated allocation even for the virtual
                # count; otherwise pending then refused allocation allow
                # the employee to create more leaves than possible
                status_dict['virtual_remaining_leaves'] += (allocation.number_of_hours_display
                                                          if allocation.type_request_unit == 'hour'
                                                          else allocation.number_of_days)
                status_dict['max_leaves'] += (allocation.number_of_hours_display
                                            if allocation.type_request_unit == 'hour'
                                            else allocation.number_of_days)
                status_dict['remaining_leaves'] += (allocation.number_of_hours_display
                                                  if allocation.type_request_unit == 'hour'
                                                  else allocation.number_of_days)
        return result