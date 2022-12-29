from odoo import api, exceptions, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT, \
    DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.addons.hr_leave_summary_request.models.hr_leave_summary_request import get_utc_datetime, get_local_datetime
from pytz import timezone, UTC
from calendar import calendar
from dateutil.relativedelta import relativedelta


class LeaveSummaryRequest(models.Model):
    _inherit = "summary.request"

    def compute_request_line(self, **args):
        employee_id = args.get('employee_id', False)
        start_date = args.get('start_date', False)
        end_date = args.get('end_date', False)

        if not (employee_id and start_date and end_date):
            return {'status': False, 'message': 'Required Parameters'}

        employee = self.env['hr.employee'].browse(employee_id)
        if not employee:
            return {'status': False, 'message': 'Employee does not exist'}

        start_date = datetime.strptime(start_date, DATE_FORMAT)
        end_date = datetime.strptime(end_date, DATE_FORMAT)
        if start_date > end_date:
            return {'status': False, 'message': 'End Date should be greater than or equal to Start Date'}

        if start_date and end_date and employee:
            resource_calendar = employee.resource_calendar_id
            tz = timezone(resource_calendar.tz)
            day_count = (end_date - start_date).days + 1

            leave_lines = []
            leave_line_obj = self.env['summary.request.line']
            for single_date in (start_date + timedelta(n) for n in range(day_count)):
                new_line_values = leave_line_obj.calculate_line_values(resource_calendar, single_date)
                for new_line_value in new_line_values:
                    date = new_line_value['date'] if isinstance(new_line_value['date'], str) else new_line_value[
                        'date'].strftime(DATE_FORMAT)
                    utc_start_date = datetime.strptime(new_line_value['start_date'], DT_FORMAT)
                    utc_end_date = datetime.strptime(new_line_value['end_date'], DT_FORMAT)
                    local_start_date = datetime.strftime(get_local_datetime(tz, utc_start_date), DT_FORMAT)
                    local_end_date = datetime.strftime(get_local_datetime(tz, utc_end_date), DT_FORMAT)
                    new_line_value.update({'request_date': date, 'date': date, 'start_date': local_start_date,
                                           'end_date': local_end_date})
                    distinct_shift = new_line_value['distinct_shift']
                    next_day_hour_id = new_line_value['next_day_hour_id']
                    new_line_value.update(
                        leave_line_obj._compute_allow_edit(single_date, start_date, end_date, next_day_hour_id,
                                                           distinct_shift))
                    leave_lines.append((new_line_value))
            return {'status': True, 'message': leave_lines}
        return {'status': False, 'message': 'Unknown Error'}

    def get_employee_calendar_date(self, employee_id=None, start_date=None, end_date=None):
        final_values = {}
        travel_obj = self.env['travel.request']
        leave_obj = self.env['hr.leave']
        training_obj = self.env['emp.training.application']
        trip_obj = self.env['plan.trip.product']
        trip_bill_obj = self.env['plan.trip.waybill']
        calendar_obj = self.env['calendar.event']
        emp_id = self.env['hr.employee'].browse([employee_id])
        leave_array = []
        travel_array = []
        training_array = []
        trip_arry = []
        trip_bill_arry = []
        calendar_arry = []
        for travel in travel_obj.search(
                [('employee_id', '=', employee_id), ('start_date', '>=', start_date), ('end_date', '<=', end_date),
                 ('state', '=', 'approve')]):
            # for travel in travel_obj.search([('employee_id','=',employee_id),('end_date','<=',end_date),('state','=','approve')]):
            travel_array.append({'employee_id': travel.employee_id.id,
                                 'start_date': travel.start_date.strftime(DATE_FORMAT),
                                 'end_date': travel.end_date.strftime(DATE_FORMAT),
                                 'name': travel.city_from or '' + '-' + travel.city_to
                                 })

        for leave in leave_obj.search([('employee_id', '=', employee_id), ('date_from', '>=', start_date + ' 00:00:00'),
                                       ('date_to', '<=', end_date + ' 23:59:59'), ('state', '=', 'validate')]):
            # for leave in leave_obj.search([('employee_id','=',employee_id),('mode_company_id','=',emp_id.company_id.id),('request_date_to','<=',end_date),('state','=','validate')]):
            leave_array.append({'employee_id': leave.employee_id.id,
                                'start_date': leave.date_from.strftime(DATE_FORMAT),
                                'end_date': leave.date_to.strftime(DATE_FORMAT),
                                'name': leave.holiday_status_id.name,
                                'leave_type': leave.holiday_status_id.name,
                                'description': leave.name or '',
                                })

        # for training in training_obj.search([('employee_id','=',employee_id),('company_id','=',emp_id.company_id.id),('start_date','>=',start_date),('end_date','<=',end_date)]):
        for training in training_obj.search(
                [('employee_id', '=', employee_id), ('company_id', '=', emp_id.company_id.id),
                 ('end_date', '<=', end_date)]):
            training_array.append({'employee_id': training.employee_id.id,
                                   'start_date': training.start_date.strftime(DATE_FORMAT),
                                   'end_date': training.end_date.strftime(DATE_FORMAT),
                                   'name': training.training_name
                                   })
        # domain = [('from_datetime','>=',start_date +' 00:00:00'),('to_datetime','<=',end_date +' 23:59:59'),('state','=','approve'),'|',('spare1_id','=',employee_id),('spare2_id','=',employee_id)]
        domain = [('to_datetime', '<=', end_date + ' 23:59:59'), ('state', '=', 'approve'), '|',
                  ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id)]
        # emp_id = self.env['hr.employee'].browse([employee_id])
        if emp_id.address_id:
            domain = [('from_datetime', '>=', start_date + ' 00:00:00'), ('to_datetime', '<=', end_date + ' 23:59:59'),
                      ('state', '=', 'approve'), '|', ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id),
                      ('driver_id', '=', emp_id.address_id.id)]
            # domain = [('to_datetime','<=',end_date +' 23:59:59'),('state','=','approve'),'|',('spare1_id','=',employee_id),('spare2_id','=',employee_id),('driver_id','=',emp_id.address_id.id)]
        for trip in trip_obj.search(domain):
            trip_arry.append({'employee_id': employee_id,
                              'start_date': trip.from_datetime.strftime(DATE_FORMAT),
                              'end_date': trip.to_datetime.strftime(DATE_FORMAT),
                              'name': trip.name
                              })

        # domain = [('from_datetime','>=',start_date +' 00:00:00'),('to_datetime','<=',end_date +' 23:59:59'),('state','=','approve'),('spare_id','=',employee_id)]
        domain = [('to_datetime', '<=', end_date + ' 23:59:59'), ('state', '=', 'approve'),
                  ('spare_id', '=', employee_id)]
        emp_id = self.env['hr.employee'].browse([employee_id])
        if emp_id.address_id:
            # domain = [('from_datetime','>=',start_date +' 00:00:00'),('to_datetime','<=',end_date +' 23:59:59'),('state','=','approve'),'|',('spare_id','=',employee_id),('driver_id','=',emp_id.address_id.id)]
            domain = [('to_datetime', '<=', end_date + ' 23:59:59'), ('state', '=', 'approve'), '|',
                      ('spare_id', '=', employee_id), ('driver_id', '=', emp_id.address_id.id)]
        for trip_bill in trip_bill_obj.search(domain):
            trip_bill_arry.append({'employee_id': employee_id,
                                   'start_date': trip_bill.from_datetime.strftime(DATE_FORMAT),
                                   'end_date': trip_bill.to_datetime.strftime(DATE_FORMAT),
                                   'name': trip_bill.name
                                   })
        for calendar_id in calendar_obj.search(
                [('name', 'ilike', emp_id.name), ('start', '>=', start_date + ' 00:00:00'),
                 ('stop', '<=', end_date + ' 23:59:59')]):
            calendar_arry.append({'employee_id': employee_id,
                                  'start_date': calendar_id.start.strftime(DATE_FORMAT),
                                  'end_date': calendar_id.stop.strftime(DATE_FORMAT),
                                  'name': calendar_id.name
                                  })
        final_values.update({
            'travel': travel_array,
            'leave': leave_array,
            'training': training_array,
            'trip_product': trip_arry,
            'trip_bill': trip_bill_arry,
            'calendar': calendar_arry
        })

        return final_values

    def create_leave_summary_request(self, employee_id=None, holiday_status_id=None, start_date=None, end_date=None,
                                     duration=None, description=None, attachment=None, file_name=None, leave_line=None):
        leave_obj = self.env['summary.request']
        leave_line_obj = self.env['summary.request.line']
        if employee_id:
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            leave_vals = {"employee_id": employee_id,
                          "company_id": employee.company_id.id,
                          "holiday_status_id": holiday_status_id,
                          "start_date": start_date,
                          "end_date": end_date,
                          "duration": duration,
                          "description": description,
                          "attachment": attachment,
                          "file_name": file_name,
                          }
            leave = leave_obj.create(leave_vals)
            if leave_line and leave:
                for line in leave_line:
                    start_date = datetime.strptime(line.get('start_date'), '%Y-%m-%d %H:%M:%S') - relativedelta(hours=6,
                                                                                                                minutes=30)
                    end_date = datetime.strptime(line.get('end_date'), '%Y-%m-%d %H:%M:%S') - relativedelta(hours=6,
                                                                                                            minutes=30)
                    leave_line_vals = {"dayofweek": line.get('dayofweek'),
                                       "date": line.get('date'),
                                       "distinct_shift": line.get('distinct_shift'),
                                       "full": line.get('full'),
                                       "first": line.get('first'),
                                       "second": line.get('second'),
                                       "start_date": start_date,
                                       "end_date": end_date,
                                       "allow_full_edit": line.get('allow_full_edit'),
                                       "allow_first_edit": line.get('allow_first_edit'),
                                       "allow_second_edit": line.get('allow_second_edit'),
                                       "this_day_hour_id": line.get('this_day_hour_id'),
                                       "next_day_hour_id": line.get('next_day_hour_id'),
                                       "request_id": leave.id
                                       }
                    leave_line = leave_line_obj.create(leave_line_vals)
                return leave_line

    def get_employee_calendar_date_new(self, employee_id=None, start_date=None, end_date=None):
        final_values = {}
        travel_obj = self.env['travel.request']
        leave_obj = self.env['hr.leave']
        training_obj = self.env['emp.training.application']
        day_trip_obj = self.env['day.plan.trip']
        plan_trip_obj = self.env['plan.trip.product']
        trip_bill_obj = self.env['plan.trip.waybill']
        calendar_obj = self.env['calendar.event']
        emp_id = self.env['hr.employee'].browse([employee_id])
        # leave_array = travel_array = training_array = day_trip_array = plan_trip_array = trip_bill_array = calendar_array = []
        leave_array = []
        travel_array = []
        training_array = []
        day_trip_array = []
        plan_trip_array = []
        trip_bill_array = []
        calendar_array = []

        for travel in travel_obj.search(
                [('employee_id', '=', employee_id), ('start_date', '>=', start_date), ('end_date', '<=', end_date),
                 ('state', '=', 'approve')]):
            travel_array.append({'employee_id': travel.employee_id.id,
                                 'start_date': travel.start_date.strftime(DATE_FORMAT),
                                 'end_date': travel.end_date.strftime(DATE_FORMAT),
                                 'name': travel.city_from or '' + '-' + travel.city_to
                                 })
        for leave in leave_obj.search(
                [('employee_id', '=', employee_id), ('date_from', '>=', str(start_date) + ' 00:00:00'),
                 ('date_to', '<=', str(end_date) + ' 23:59:59'), ('state', '=', 'validate')]):
            leave_array.append({'employee_id': leave.employee_id.id,
                                'start_date': leave.date_from.strftime(DATE_FORMAT),
                                'end_date': leave.date_to.strftime(DATE_FORMAT),
                                'name': leave.holiday_status_id.name,
                                'leave_type': leave.holiday_status_id.name,
                                'description': leave.name or '',
                                })
        for training in training_obj.search([('end_date', '<=', end_date)]):
            for emp in training.employee_ids:
                if emp.id == employee_id:
                    training_array.append({'employee_id': emp.id,
                                           'start_date': training.start_date.strftime(DATE_FORMAT),
                                           'end_date': training.end_date.strftime(DATE_FORMAT),
                                           'name': training.training_name
                                           })
        domain = [('from_datetime', '>=', str(start_date) + ' 00:00:00'),
                  ('to_datetime', '<=', str(end_date) + ' 23:59:59'), ('state', '=', 'open'),
                  ('driver_id', '=', employee_id)]
        for day_trip in day_trip_obj.search(domain):
            day_trip_array.append({'employee_id': day_trip.driver_id.id,
                                   'start_date': day_trip.from_datetime.strftime(DATE_FORMAT),
                                   'end_date': day_trip.to_datetime.strftime(DATE_FORMAT),
                                   'name': day_trip.code
                                   })
        for plan_trip in plan_trip_obj.search(domain):
            plan_trip_array.append({'employee_id': plan_trip.driver_id.id,
                                    'start_date': plan_trip.from_datetime.strftime(DATE_FORMAT),
                                    'end_date': plan_trip.to_datetime.strftime(DATE_FORMAT),
                                    'name': plan_trip.code
                                    })
        for plan_trip in trip_bill_obj.search(domain):
            trip_bill_array.append({'employee_id': plan_trip.driver_id.id,
                                    'start_date': plan_trip.from_datetime.strftime(DATE_FORMAT),
                                    'end_date': plan_trip.to_datetime.strftime(DATE_FORMAT),
                                    'name': plan_trip.code
                                    })
        for calendar_id in calendar_obj.search(
                [('name', 'ilike', emp_id.name), ('start', '>=', str(start_date) + ' 00:00:00'),
                 ('stop', '<=', str(end_date) + ' 23:59:59')]):
            for emp in calendar_id.employee_ids:
                if emp.id == employee_id:
                    calendar_array.append({'employee_id': emp.id,
                                           'start_date': calendar_id.start.strftime(DATE_FORMAT),
                                           'end_date': calendar_id.stop.strftime(DATE_FORMAT),
                                           'name': calendar_id.name
                                           })
        final_values.update({
            'travel': travel_array,
            'leave': leave_array,
            'training': training_array,
            'day_trip': day_trip_array,
            'trip_product': plan_trip_array,
            'trip_bill': trip_bill_array,
            'calendar': calendar_array
        })

        return final_values


class LeaveLine(models.Model):
    _inherit = 'summary.request.line'

    def update_request_line(self, **args):
        request_date = args.get('date')
        request_date = datetime.strptime(request_date, DATE_FORMAT) if isinstance(request_date, str) else request_date
        this_day_hour_id = args.get('this_day_hour_id')
        next_day_hour_id = args.get('next_day_hour_id')
        distinct_shift = args.get('distinct_shift', '')
        first = args.get('first', False)
        second = args.get('second', False)
        full = args.get('full', False)

        if distinct_shift == 'morning' and (full or second):
            return {'status': False, 'message': 'This leave request has only first half day.'}
        if distinct_shift == 'afternoon' and (full or first):
            return {'status': False, 'message': 'This leave request has only second half day.'}
        try:
            start_date, end_date = self.with_context(via='mobile').manipulate_options(request_date, this_day_hour_id,
                                                                                      next_day_hour_id, distinct_shift,
                                                                                      first, second)
            args.update({'start_date': start_date.strftime(DT_FORMAT), 'end_date': end_date.strftime(DT_FORMAT)})
            return {'status': True, 'message': args}
        except:
            return {'status': False, 'message': 'Something Wrong!'}
