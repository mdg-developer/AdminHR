from odoo import api, exceptions, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.addons.hr_travel_request.models.hr_travel_request import get_utc_datetime, get_local_datetime
from pytz import timezone, UTC


class TravelRequest(models.Model):
    _inherit = 'travel.request'

    def compute_request_line(self, **args):
        employee_id = args.get('employee_id', False)
        start_date = args.get('start_date', False)
        end_date = args.get('end_date', False)

        if not(employee_id and start_date and end_date):
            return {'status': False, 'message': 'Required Parameters'}

        employee = self.env['hr.employee'].browse(employee_id)
        if not employee:
            return {'status': False, 'message': 'Employee does not exist'}

        start_date = datetime.strptime(start_date, DATE_FORMAT)
        end_date = datetime.strptime(end_date, DATE_FORMAT)
        if start_date > end_date:
            return {'status': False, 'message': 'End Date should be greater than or equal to Start Date'}

        if start_date and end_date and employee:
            resource_calendar = employee.contract_id and employee.contract_id.resource_calendar_id or employee.resource_calendar_id
            tz = timezone(resource_calendar.tz)
            day_count = (end_date - start_date).days + 1

            travel_lines = []
            travel_line_obj = self.env['travel.request.line']
            for single_date in (start_date + timedelta(n) for n in range(day_count)):
                new_line_values = travel_line_obj.calculate_line_values(resource_calendar, single_date)
                for new_line_value in new_line_values:
                    date = new_line_value['date'] if isinstance(new_line_value['date'], str) else new_line_value['date'].strftime(DATE_FORMAT)
                    utc_start_date = datetime.strptime(new_line_value['start_date'], DT_FORMAT)
                    utc_end_date = datetime.strptime(new_line_value['end_date'], DT_FORMAT)
                    local_start_date = datetime.strftime(get_local_datetime(tz, utc_start_date), DT_FORMAT)
                    local_end_date = datetime.strftime(get_local_datetime(tz, utc_end_date), DT_FORMAT)
                    new_line_value.update({'date': date, 'start_date': local_start_date, 'end_date': local_end_date})
                    distinct_shift = new_line_value['distinct_shift']
                    next_day_hour_id = new_line_value['next_day_hour_id']
                    this_day_hour_id = new_line_value['this_day_hour_id']
                    new_line_value.update(travel_line_obj._compute_allow_edit(single_date, start_date, end_date, this_day_hour_id, next_day_hour_id, distinct_shift))
                    travel_lines.append((new_line_value))
            return {'status': True, 'message': travel_lines}
        return {'status': False, 'message': 'Unknown Error'}


class TravelLine(models.Model):
    _inherit = 'travel.request.line'

    def update_travel_line(self, **args):
        request_date = args.get('date')
        request_date = datetime.strptime(request_date, DATE_FORMAT) if isinstance(request_date, str) else request_date
        this_day_hour_id = args.get('this_day_hour_id')
        next_day_hour_id = args.get('next_day_hour_id')
        distinct_shift = args.get('distinct_shift', '')
        first = args.get('first', False)
        second = args.get('second', False)
        full = args.get('full', False)

        if distinct_shift == 'morning' and (full or second):
            return {'status': False, 'message': 'This travel request has only first half day.'}
        if distinct_shift == 'afternoon' and (full or first):
            return {'status': False, 'message': 'This travel request has only second half day.'}
        try:
            start_date, end_date = self.with_context(via='mobile').manipulate_options(request_date, this_day_hour_id, next_day_hour_id, distinct_shift, first, second)
            args.update({'start_date': start_date.strftime(DT_FORMAT), 'end_date': end_date.strftime(DT_FORMAT)})
            return {'status': True, 'message': args}
        except:
            return {'status': False, 'message': 'Something Wrong!'}
