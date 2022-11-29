import math
from datetime import datetime, date, time, timedelta
from odoo import fields, models, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
from pytz import timezone, UTC
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
import pytz

def float_to_time(value):
    if value < 0:
        value = abs(value)

    hour = int(value)
    minute = round((value % 1) * 60)

    if minute == 60:
        minute = 0
        hour = hour + 1
    return time(hour, minute)


def time_to_float(value):
    return value.hour + value.minute / 60 #+ value.second / 3600


class HrAttendance(models.Model):    
    _inherit = 'hr.attendance'    
    _description = 'Attendance Form Customization'

    late_minutes = fields.Float(string='Late Minutes', compute='_compute_work_hours', digits=dp.get_precision('Payroll'), store=True)
    early_out_minutes = fields.Float(string='Early Out Minutes', compute='_compute_work_hours', digits=dp.get_precision('Payroll'), store=True)
    ot_hour = fields.Float(string='OT hour', compute='_compute_work_hours', store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('decline', 'Decline'),
                              ('approve', 'Approved'),
                              ('verify', 'Verified')], default='draft', copy=False, required=True)
    enable_approval = fields.Boolean('Enable Approval', compute='_compute_enable_approval')
    is_absent = fields.Boolean('Is Absent', default=False)
    early_ot_hour = fields.Float(string='Early OT Hours', compute='_compute_work_hours', store=True)
    leave = fields.Boolean("Leave", default=False)
    travel = fields.Boolean("Travel", default=False)
    plan_trip = fields.Boolean("Plan Trip", default=False)
    day_trip = fields.Boolean("Day Trip", default=False)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Schedule', related='employee_id.resource_calendar_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='employee_id.company_id', store=True)
    no_worked_day = fields.Boolean("No Work Day Leave", default=False)
    remark = fields.Text("Remark")
        
    @api.onchange('no_worked_day')
    def _no_worked_day(self):
        for att in self:
            if att.no_worked_day == True:
                att.is_absent = False
    
    @api.onchange('is_absent')
    def _is_absent(self):
        for att in self:
            if att.is_absent == True:
                att.no_worked_day = False
                            
    @api.depends('employee_id')
    @api.depends_context('employee_id')
    def _compute_enable_approval(self):
        for req in self:
            if self.env.context.get('employee_id'):
                domain = [('id', '=', self.env.context.get('employee_id'))]
            else:
                domain = [('user_id', '=', self.env.user.id)]
            employee = self.env['hr.employee'].search(domain, limit=1)
            # is_approval_manager = self.env['hr.employee'].search([('approve_manager', '=', employee.id)]) and True or False
            # if employee and req.employee_id.approve_manager == employee or is_approval_manager and req.employee_id == employee:
            if employee and req.employee_id.approve_manager == employee:
                req.enable_approval = True
            else:
                req.enable_approval = False
                
    def admin_trip(self,att):
        day_trip = plan_trip = False
        remark = ""
        if att.employee_id.day_trip_id:
            day_trip = True
            remark = att.employee_id.day_trip_id.code + '\n' + str(att.employee_id.day_trip_id.from_datetime + timedelta(hours=+6,minutes=+30))
            if att.employee_id.day_trip_id.to_datetime:
                remark += '\n' + str(att.employee_id.day_trip_id.to_datetime + timedelta(hours=+6,minutes=+30))
        elif att.employee_id.plan_trip_waybill_id:
            plan_trip = True
            remark = att.employee_id.plan_trip_waybill_id.code + '\n' + str(att.employee_id.plan_trip_waybill_id.from_datetime + timedelta(hours=+6,minutes=+30))
            if att.employee_id.plan_trip_waybill_id.to_datetime:
                remark += '\n' + str(att.employee_id.plan_trip_waybill_id.to_datetime + timedelta(hours=+6,minutes=+30))
        elif att.employee_id.plan_trip_product_id:
            plan_trip = True
            remark = att.employee_id.plan_trip_product_id.code + '\n' + str(att.employee_id.plan_trip_product_id.from_datetime + timedelta(hours=+6,minutes=+30))
            if att.employee_id.plan_trip_product_id.to_datetime:
                remark += '\n' + str(att.employee_id.plan_trip_product_id.to_datetime + timedelta(hours=+6,minutes=+30))
        return day_trip,plan_trip,remark
    
    @api.depends('check_in', 'check_out')
    def _compute_work_hours(self):
        for att in self:
            att.late_minutes = att.early_out_minutes = att.ot_hour = att.early_ot_hour = 0
            remark = ""
            day_trip,plan_trip,remark = self.admin_trip(att)
            if len(remark) > 0:
                att.remark = remark

            att.day_trip = day_trip
            att.plan_trip = plan_trip
            if att.check_in and att.check_out:
                att.missed = False
                beg_date = att.check_in + timedelta(hours=+6,minutes=+30)
                public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date.date()),'|',
                                                                      ('line_id.company_id', '=', att.employee_id.company_id.id), ('line_id.company_id', '=', False)], order='id desc', limit=1)
                if public_holiday:
                    att.late_minutes =  0
                    att.early_ot_hour =  0
                    continue
                if att.plan_trip == True or att.day_trip == True:
                    #att.late_minutes =  0
                    #att.early_ot_hour =  0
                    att.is_absent = False
                    att.missed = False
                    continue
                
                calendar = att.employee_id.resource_calendar_id
                tz = timezone(calendar.tz)
                check_in = att.check_in + timedelta(hours=+6,minutes=+30)#att.check_in.astimezone(tz)
                check_out = att.check_out + timedelta(hours=+6,minutes=+30)#att.check_out.astimezone(tz)
                in_float = time_to_float(check_in)
                out_float = time_to_float(check_out)
                dayofweek = check_in.weekday()                
                day_period = in_float < 12 and 'morning' or 'afternoon'

                domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', calendar.id),
                          ('dayofweek', '=', str(dayofweek)), ('day_period', '=', day_period)]
                if calendar.two_weeks_calendar:
                    week_type = int(math.floor((check_in.toordinal() - 1) / 7) % 2)
                    domain += [('week_type', '=', str(week_type))]

                working_hours = self.env['resource.calendar.attendance'].search(domain)
                for wh in working_hours:
                    hour_from = wh.hour_from + 0.000001
                    hour_to = wh.hour_to + 0.000001
                    in_diff = out_diff = 0
                    if round(wh.hour_from) == 0:
                        out_diff = hour_to - out_float
                    elif round(wh.hour_to) == 24:
                        in_diff = in_float - hour_from
                    else:
                        in_diff = in_float - hour_from
                        out_diff = hour_to - out_float

                    att.late_minutes = in_diff > 0 and in_diff or 0
                    att.early_ot_hour = in_diff < 0 and abs(in_diff) or 0
                    att.early_out_minutes = out_diff > 0 and out_diff or 0
                    att.ot_hour = out_diff < 0 and abs(out_diff) or 0

    def decline(self):
        self.state = 'decline'

    def approve(self):
        self.state = 'approve'

    def verify(self):
        self.state = 'verify'

    def approve_attendances(self, force_approve=False):
        domain = []
        if not force_approve:
            domain = [('state', '=', 'draft')]
        if self._context.get('active_ids'):
            domain += [('id', 'in', self._context.get('active_ids'))]

        attendances = self.search(domain, order='check_in asc')
        for attendance in attendances:
            if force_approve:
                attendance.state = 'approve'
                if attendance.employee_id.no_need_attendance == True:
                    attendance.is_absent = False
            elif attendance.late_minutes or attendance.early_out_minutes or attendance.is_absent or attendance.missed:
                attendance.state = 'decline'
            else:
                attendance.state = 'approve'
                if attendance.employee_id.no_need_attendance == True:
                    attendance.is_absent = False            
            
    
    def approve_attendances_last_week(self, force_approve=False):
        domain = []
        user_tz = timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        
        current_date = today.astimezone(timezone('UTC'))
        yesterday = current_date - timedelta(days=1)
        today = current_date #- timedelta(days=0)
        date_stop = yesterday + timedelta(days=1, seconds=-1)
        #date_stop = before_7day + timedelta(days=1, seconds=-1)
        domain = [('state', '=', 'draft'),('check_in','<=',date_stop)]
        #print(today)
        from_date = today - timedelta(days=7)
        to_date = today.date()
        from_date = from_date.date()
        #print(from_date,to_date)
        self.env.cr.execute("""
        update hr_attendance set is_absent='f' where is_absent='t' and (extract(second from check_in) <> 0 or extract(second from check_out) <> 0)
        and state in('draft','approve') and check_in::date >=%s and check_in::date <=%s
        """,(from_date,to_date,))
        
        attendances = self.search(domain, order='check_in asc')
        for attendance in attendances:
            attendance.state = 'approve'
            if attendance.employee_id.no_need_attendance == True:
                attendance.is_absent = False
#         date_stop = datetime.now() + timedelta(days=1, hours=-6) 
        #date_and_time  = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 7, 0, 0)
        date_and_time  = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 11, 0, 0)
        print(date_and_time)
#         beg_date = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
#         date_stop = datetime.combine(beg_date, float_to_time(8)) 
#         date_stop = datetime.now() + relativedelta(hours=15, minutes=00, seconds=00)
        domain = [('state', '=', 'draft'),('check_in','<=',date_and_time)] 
        attendances = self.search(domain, order='check_in asc')
        for attendance in attendances:
            attendance.state = 'approve'
            if attendance.id == 159605:
                print("i catch u")
            if attendance.employee_id.no_need_attendance == True:
                attendance.is_absent = False
         
                
    def verify_attendances(self):
        domain = [('state', 'in', ('approve', 'decline'))]
        if self._context.get('active_ids'):
            domain += [('id', 'in', self._context.get('active_ids'))]
        attendances = self.search(domain, order='check_in asc')
        for attendance in attendances:
            attendance.state = 'verify'

    def decline_attendances(self):
        domain = ['|', '|', '|', ('late_minutes', '>', 0), ('early_out_minutes', '>', 0), ('is_absent', '=', True), ('missed', '=', True)]
        if self._context.get('active_ids'):
            domain += [('id', 'in', self._context.get('active_ids'))]
        attendances = self.search(domain, order='check_in asc')
        for attendance in attendances:
            attendance.state = 'decline'
    def check_trip(self,attendance_id):
        driver_id = False
        if attendance_id.employee_id.address_home_id:
            driver_id = attendance_id.employee_id.address_home_id.id or False
            
        trip = self.env['day.plan.trip'].search([('from_datetime','<=',attendance_id.check_in),('to_datetime','>=',attendance_id.check_out),('state','in',['open','running']),'|',('driver_id','=',attendance_id.employee_id.id),('spare1_id','=',attendance_id.employee_id.id),('spare2_id','=',attendance_id.employee_id.id)],limit=1)
        if trip: 
            attendance_id.write({'is_absent':False,'day_trip':True})
        
        plantrip = self.env['plan.trip.waybill'].search([('from_datetime','<=',attendance_id.check_in),('to_datetime','>=',attendance_id.check_out),('state','in',['open','running']),'|',('driver_id','=',driver_id),('spare_id','=',attendance_id.employee_id.id)],limit=1)
        if plantrip: 
            attendance_id.write({'is_absent':False,'plan_trip':True}) 
        
        waybill = self.env['plan.trip.waybill'].search([('from_datetime','<=',attendance_id.check_in),('to_datetime','>=',attendance_id.check_out),('state','in',['open','running']),'|',('driver_id','=',driver_id),('spare_id','=',attendance_id.employee_id.id)],limit=1)
        if trip: 
            attendance_id.write({'is_absent':False,'plan_trip':True})     
    
    def check_absent(self,working_hours,yesterday,tz,emp):
        working_hour = 0
        attendance = []
        if len(working_hours) == 2:
            for wh in working_hours:
                check_in = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_from)), is_dst=True).astimezone(tz=UTC)
                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                #attendance_id = self.create({'employee_id': emp.id, 'check_in': check_in.strftime(DT), 'check_out': check_out.strftime(DT), 'is_absent': True})
                attendances = self.env['hr.attendance'].search([('employee_id', '=', emp.id),
                                                                    ('check_in', '>=', check_in.strftime(DT)),
                                                                    ('check_in', '<', check_out.strftime(DT))])
                if not attendances:
                    attendance.append(wh.id)
            if len(attendance) == 1:
                return attendance[0]
        return working_hour                        
    def check_leave_or_travel(self,attendance_id):
        print(attendance_id.check_in.date())
        print(attendance_id.check_out.date())
        print(attendance_id.check_in)
        print(attendance_id.check_out)
        leave = self.env['hr.leave'].search([('date_from','<=',attendance_id.check_in),('date_to','>=',attendance_id.check_out),('state','in',['validate','validate1']),('employee_id','=',attendance_id.employee_id.id)],limit=1)
        #leave = self.env['hr.leave'].search([('request_date_from','<=',attendance_id.check_in),('request_date_to','>=',attendance_id.check_out),('state','in',['validate','validate1']),('employee_id','=',attendance_id.employee_id.id)],limit=1)
        if leave:
            if leave.holiday_status_id.travel_leave == True:
                attendance_id.write({'is_absent':False,'travel':True})
#             elif leave.holiday_status_id.one_day_off == True or leave.holiday_status_id.no_holidays == True:
#                 attendance_id.write({'is_absent':False,'no_worked_day':True})
            else:
                attendance_id.write({'is_absent':False,'leave':True})
                
    def recreate_absent_no_need_attendances(self,from_date,to_date):
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        print(fields.Datetime.now())
        current = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz)
        print(current)
        yesterday = current.date() - timedelta(days=1)
        print(yesterday)
        dayofweek = yesterday.weekday()
        print(dayofweek)
        
        self.env.cr.execute("""
        SELECT date_trunc('day', dd):: date
            FROM generate_series
                    ( %s::timestamp 
                    , %s::timestamp
                    , '1 day'::interval) dd
        """,(from_date,to_date,))
        results = self.env.cr.dictfetchall()
        
        date_list = []
        for data in results:
            t_date = data['date_trunc']
            date_list.append(t_date)
        #print(date_list)
        try:
            for yesterday in date_list: 
                dayofweek = yesterday.weekday()
                for emp in self.env['hr.employee'].sudo().search([('no_need_attendance', '=', True)]):
                #for emp in self.env['hr.employee'].search([('id', '=', 6160)]):
                    holiday = self.env['public.holidays.line'].sudo().search([('date','=',yesterday)],limit=1)
                    if holiday:
                        continue
                    if emp.resource_calendar_id:
                        tz = timezone(emp.resource_calendar_id.tz or 'Asia/Yangon')
                        date_start = tz.localize(fields.Datetime.to_datetime(yesterday), is_dst=True).astimezone(tz=UTC)
                        date_stop = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), datetime.max.time()), is_dst=True).astimezone(tz=UTC)
                        print(date_start)
                        print(date_stop)
                        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', emp.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                        if emp.resource_calendar_id.two_weeks_calendar:
                            week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                            domain += [('week_type', '=', str(week_type))]
        
                        working_hours = self.env['resource.calendar.attendance'].search(domain)
                        if working_hours:
                            attendances = self.env['hr.attendance'].sudo().search([('employee_id', '=', emp.id),
                                                                            ('check_in', '>=', date_start),
                                                                            ('check_in', '<', date_stop)])
                            if not attendances:
                                for wh in working_hours:
                                    first_time = True
                                    check_in = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    working_time = self.check_absent(working_hours,yesterday,tz,emp)
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': check_in.strftime(DT), 'check_out': check_out.strftime(DT), 'is_absent': False})
                                    
                                    if working_time != 0 and wh.id==working_time:
                                        attendance_id.write({'is_absent':True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                                    print("create attendance absent>>>>",attendance_id)
                            elif len(working_hours) > len(attendances):
                                distinct = morn_start = morn_end = night_start = night_end = dist_start = dist_end = False
                                morning = working_hours.filtered(lambda h: round(h.hour_from) == 0)
                                night = working_hours.filtered(lambda h: round(h.hour_to) == 24)
                                distincts = working_hours.filtered(lambda h: round(h.hour_from) != 0 and round(h.hour_to) != 24)
                                if len(distincts) == 1:
                                    distinct = distincts
                                if morning:
                                    morn_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    morn_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_to)), is_dst=True).astimezone(tz=UTC)
        
                                if night:
                                    night_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    night_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_to)), is_dst=True).astimezone(tz=UTC)
        
                                if distinct:
                                    dist_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    dist_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_to)), is_dst=True).astimezone(tz=UTC)
        
                                if morning and night:
                                    if not attendances.filtered(lambda att: morn_start <= att.check_in < morn_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': morn_start.strftime(DT), 'check_out': morn_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                    elif not attendances.filtered(lambda att: night_start < att.check_out <= night_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                elif morning and distinct:
                                    if not attendances.filtered(lambda att: morn_start <= att.check_in < morn_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': morn_start.strftime(DT), 'check_out': morn_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                    else:
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                elif distinct and night:
                                    if not attendances.filtered(lambda att: att.check_out != False and night_start < att.check_out <= night_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                    else:
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                else:
                                    for dist in distincts:
                                        hr_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_from)), is_dst=True).astimezone(tz=UTC)
                                        hr_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_to)), is_dst=True).astimezone(tz=UTC)
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': hr_start.strftime(DT), 'check_out': hr_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                            self._cr.commit()
        except ValidationError as e:
            value = {
                     'employee_id':emp.id,
                     'company_id':emp.company_id.id,
                     'date':yesterday,
                     'log':e.name
                     }
            log_id = self.env['absent.log'].create(value)

    def recreate_attendance_log_date(self, force_approve=False):

        self.env.cr.execute("""
                SELECT distinct date
                    FROM absent_log
                            order by date
                """)
        results = self.env.cr.dictfetchall()
        for data in results:
            t_date = data['date']
            self.env.cr.execute("""
                    select id from hr_employee where id not in (select employee_id from hr_attendance
                    where (check_in::timestamp without time zone + interval '6 hours 30 minutes')::date=%s) and joining_date <= %s
                    """, (t_date,t_date,))
            res_emplist = self.env.cr.dictfetchall()
            emp_list = []
            for employee in res_emplist:
                emp_list.append(employee['id'])
            if len(emp_list) > 0:
                self.recreate_absent_attendances(t_date,t_date,emp_list)
            for absent in self.env['absent.log'].sudo().search([('date','=',t_date)]):
                absent.unlink()


    def recreate_absent_attendances(self,from_date,to_date,employee_id):
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        print(fields.Datetime.now())
        current = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz)
        print(current)
        yesterday = current.date() - timedelta(days=1)
        print(yesterday)
        dayofweek = yesterday.weekday()
        print(dayofweek)
        
        self.env.cr.execute("""
        SELECT date_trunc('day', dd):: date
            FROM generate_series
                    ( %s::timestamp 
                    , %s::timestamp
                    , '1 day'::interval) dd
        """,(from_date,to_date,))
        results = self.env.cr.dictfetchall()
        
        date_list = []
        for data in results:
            t_date = data['date_trunc']
            date_list.append(t_date)
        #print(date_list)
        if employee_id != False:
            emp_domain = [('id','in',employee_id)]
        else:
            emp_domain = []
        try:
            for yesterday in date_list: 
                dayofweek = yesterday.weekday()
                for emp in self.env['hr.employee'].sudo().browse(employee_id):
                #for emp in self.env['hr.employee'].search([('id', '=', 6160)]):
                    holiday = self.env['public.holidays.line'].sudo().search([('date','=',yesterday)],limit=1)
                    if holiday:
                        continue
                    if emp.joining_date and emp.joining_date > yesterday:
                        continue
                    if emp.resign_date and emp.resign_date < yesterday:
                        continue

                    if emp.resource_calendar_id:
                        tz = timezone(emp.resource_calendar_id.tz or 'Asia/Yangon')
                        date_start = tz.localize(fields.Datetime.to_datetime(yesterday), is_dst=True).astimezone(tz=UTC)
                        date_stop = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), datetime.max.time()), is_dst=True).astimezone(tz=UTC)
                        print(date_start)
                        print(date_stop)
                        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', emp.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                        if emp.resource_calendar_id.two_weeks_calendar:
                            week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                            domain += [('week_type', '=', str(week_type))]
        
                        working_hours = self.env['resource.calendar.attendance'].search(domain)
                        if working_hours:
                            attendances = self.env['hr.attendance'].search([('employee_id', '=', emp.id),
                                                                            ('check_in', '>=', date_start),
                                                                            ('check_in', '<', date_stop)])
                            if not attendances:
                                for wh in working_hours:
                                    first_time = True
                                    check_in = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    working_time = self.check_absent(working_hours,yesterday,tz,emp)
                                    val = {'employee_id': emp.id, 'check_in': check_in.strftime(DT), 'check_out': check_out.strftime(DT), 'is_absent': True}
                                    print("val>>>",val)
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': check_in.strftime(DT), 'check_out': check_out.strftime(DT), 'is_absent': True})
                                    
                                    if working_time != 0 and wh.id==working_time:
                                        attendance_id.write({'is_absent':True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                                    print("create attendance absent>>>>",attendance_id)
                            elif len(working_hours) > len(attendances):
                                continue
                                distinct = morn_start = morn_end = night_start = night_end = dist_start = dist_end = False
                                morning = working_hours.filtered(lambda h: round(h.hour_from) == 0)
                                night = working_hours.filtered(lambda h: round(h.hour_to) == 24)
                                distincts = working_hours.filtered(lambda h: round(h.hour_from) != 0 and round(h.hour_to) != 24)
                                if len(distincts) == 1:
                                    distinct = distincts
                                if morning:
                                    morn_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    morn_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    morn_start = morn_start.strptime(str(morn_start),"%Y-%m-%d %H:%M:%S%z")                                    
                                    morn_start = morn_start.strftime('%Y-%m-%d %H:%M:%S')
                                    morn_start = datetime.strptime(morn_start,'%Y-%m-%d %H:%M:%S')
                                    morn_end = morn_end.strptime(str(morn_end),"%Y-%m-%d %H:%M:%S%z")                                    
                                    morn_end = morn_end.strftime('%Y-%m-%d %H:%M:%S')
                                    morn_end = datetime.strptime(morn_end,'%Y-%m-%d %H:%M:%S')
                                    
                                if night:
                                    night_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    night_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    night_start = night_start.strptime(str(night_start),"%Y-%m-%d %H:%M:%S%z")                                    
                                    night_start = night_start.strftime('%Y-%m-%d %H:%M:%S')
                                    night_start = datetime.strptime(night_start,'%Y-%m-%d %H:%M:%S')
                                    night_end = night_end.strptime(str(night_end),"%Y-%m-%d %H:%M:%S%z")                                    
                                    night_end = night_end.strftime('%Y-%m-%d %H:%M:%S')
                                    night_end = datetime.strptime(night_end,'%Y-%m-%d %H:%M:%S')
                                if distinct:
                                    dist_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    dist_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    dist_start = dist_start.strptime(str(dist_start),"%Y-%m-%d %H:%M:%S%z")                                    
                                    dist_start = dist_start.strftime('%Y-%m-%d %H:%M:%S')                                
                                    dist_start = datetime.strptime(dist_start,'%Y-%m-%d %H:%M:%S')                                    
                                    dist_end = dist_end.strptime(str(dist_end),"%Y-%m-%d %H:%M:%S%z")                                    
                                    dist_end = dist_end.strftime('%Y-%m-%d %H:%M:%S')                                
                                    dist_end = datetime.strptime(dist_end,'%Y-%m-%d %H:%M:%S')
        
                                if morning and night:
                                    if not attendances.filtered(lambda att: morn_start <= att.check_in < morn_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': morn_start.strftime(DT), 'check_out': morn_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                    elif not attendances.filtered(lambda att: night_start < att.check_out <= night_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                elif morning and distinct:
                                    if not attendances.filtered(lambda att: morn_start <= att.check_in < morn_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': morn_start.strftime(DT), 'check_out': morn_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                    else:
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                elif distinct and night:
                                    if not attendances.filtered(lambda att: att.check_out != False and night_start < att.check_out <= night_end):
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                    else:
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                                else:
                                    for dist in distincts:
                                        hr_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_from)), is_dst=True).astimezone(tz=UTC)
                                        hr_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_to)), is_dst=True).astimezone(tz=UTC)
                                        attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': hr_start.strftime(DT), 'check_out': hr_end.strftime(DT), 'is_absent': True})
                                        self.check_leave_or_travel(attendance_id)
                                        self.check_trip(attendance_id)
                            self._cr.commit()
        except Exception:
            value = {
                     'employee_id':emp.id,
                     'company_id':emp.company_id.id,
                     'date':yesterday,
                    
                     }
            log_id = self.env['absent.log'].create(value)
    def create_absent_attendances(self):
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        print(fields.Datetime.now())
        current = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz)
        print(current)        
        yesterday = current.date() - timedelta(days=1) 
        #date_time_str = '2021-10-10'
        #yesterday = datetime.strptime(date_time_str, '%Y-%m-%d').date()       
        print(yesterday)
        dayofweek = yesterday.weekday()
        print(dayofweek)
        try:
            for emp in self.env['hr.employee'].sudo().search([]):
                if emp.id == 6111:
                    print("hello")
            #for emp in self.env['hr.employee'].search([('no_need_attendance', '=', False)]):
            #for emp in self.env['hr.employee'].search([('id', '=', 6158)]):
                holiday = self.env['public.holidays.line'].sudo().search([('date','=',yesterday)],limit=1)
                if holiday:
                    continue
                if emp.resource_calendar_id:
                    tz = timezone(emp.resource_calendar_id.tz or 'Asia/Yangon')
                    date_start = tz.localize(fields.Datetime.to_datetime(yesterday), is_dst=True).astimezone(tz=UTC)
                    date_stop = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), datetime.max.time()), is_dst=True).astimezone(tz=UTC)
                    print(date_start)
                    print(date_stop)
                    domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', emp.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                    if emp.resource_calendar_id.two_weeks_calendar:
                        week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                        domain += [('week_type', '=', str(week_type))]
    
                    working_hours = self.env['resource.calendar.attendance'].search(domain)
                    if working_hours:
                        attendances = self.env['hr.attendance'].sudo().search([('employee_id', '=', emp.id),
                                                                        ('check_in', '>=', date_start),
                                                                        ('check_in', '<', date_stop)])
                        if not attendances:
                            for wh in working_hours:
                                first_time = True
                                check_in = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_from)), is_dst=True).astimezone(tz=UTC)
                                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                working_time = self.check_absent(working_hours,yesterday,tz,emp)
                                attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': check_in.strftime(DT), 'check_out': check_out.strftime(DT), 'is_absent': True})
                                
                                if working_time != 0 and wh.id==working_time:
                                    attendance_id.write({'is_absent':True})
                                self.check_leave_or_travel(attendance_id)
                                self.check_trip(attendance_id)
                        elif len(working_hours) > len(attendances):
                            distinct = morn_start = morn_end = night_start = night_end = dist_start = dist_end = False
                            morning = working_hours.filtered(lambda h: round(h.hour_from) == 0)
                            night = working_hours.filtered(lambda h: round(h.hour_to) == 24)
                            distincts = working_hours.filtered(lambda h: round(h.hour_from) != 0 and round(h.hour_to) != 24)
                            if len(distincts) == 1:
                                distinct = distincts
                            if morning:
                                morn_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_from)), is_dst=True).astimezone(tz=UTC)
                                morn_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_to)), is_dst=True).astimezone(tz=UTC)
                                
                                morn_start = morn_start.strptime(str(morn_start),"%Y-%m-%d %H:%M:%S%z")                                    
                                morn_start = morn_start.strftime('%Y-%m-%d %H:%M:%S')
                                morn_start = datetime.strptime(morn_start,'%Y-%m-%d %H:%M:%S')
                                
                                morn_end = morn_end.strptime(str(morn_end),"%Y-%m-%d %H:%M:%S%z")                                    
                                morn_end = morn_end.strftime('%Y-%m-%d %H:%M:%S')
                                morn_end = datetime.strptime(morn_end,'%Y-%m-%d %H:%M:%S')
                                
                            if night:
                                night_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_from)), is_dst=True).astimezone(tz=UTC)
                                night_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_to)), is_dst=True).astimezone(tz=UTC)
                                
                                night_start = night_start.strptime(str(night_start),"%Y-%m-%d %H:%M:%S%z")                                    
                                night_start = night_start.strftime('%Y-%m-%d %H:%M:%S')
                                night_start = datetime.strptime(night_start,'%Y-%m-%d %H:%M:%S')
                                
                                night_end = night_end.strptime(str(night_end),"%Y-%m-%d %H:%M:%S%z")                                    
                                night_end = night_end.strftime('%Y-%m-%d %H:%M:%S')
                                night_end = datetime.strptime(night_end,'%Y-%m-%d %H:%M:%S')
                            if distinct:
                                dist_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_from)), is_dst=True).astimezone(tz=UTC)
                                dist_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_to)), is_dst=True).astimezone(tz=UTC)
                                
                                dist_start = dist_start.strptime(str(dist_start),"%Y-%m-%d %H:%M:%S%z")                                    
                                dist_start = dist_start.strftime('%Y-%m-%d %H:%M:%S')                                
                                dist_start = datetime.strptime(dist_start,'%Y-%m-%d %H:%M:%S')
                                
                                dist_end = dist_end.strptime(str(dist_end),"%Y-%m-%d %H:%M:%S%z")                                    
                                dist_end = dist_end.strftime('%Y-%m-%d %H:%M:%S')                                
                                dist_end = datetime.strptime(dist_end,'%Y-%m-%d %H:%M:%S')
                            if morning and night:
                                                                
                                if attendances.id ==271164:
                                    print('check>>>',attendances.check_in )                                    
                                   
                                if not attendances.filtered(lambda att: morn_start <= att.check_in < morn_end):
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': morn_start.strftime(DT), 'check_out': morn_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                                elif not attendances.filtered(lambda att: night_start < att.check_out <= night_end):
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                            elif morning and distinct:
                                if not attendances.filtered(lambda att: morn_start <= att.check_in < morn_end):
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': morn_start.strftime(DT), 'check_out': morn_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                                else:
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                            elif distinct and night:
                                if not attendances.filtered(lambda att: night_start < att.check_out <= night_end):
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                                else:
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                            else:
                                for dist in distincts:
                                    hr_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    hr_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    attendance_id = self.sudo().create({'employee_id': emp.id, 'check_in': hr_start.strftime(DT), 'check_out': hr_end.strftime(DT), 'is_absent': True})
                                    self.check_leave_or_travel(attendance_id)
                                    self.check_trip(attendance_id)
                        self._cr.commit()
        except Exception:
            value = {
                     'employee_id':emp.id,
                     'company_id':emp.company_id.id,
                     'date':yesterday
                     }
            log_id = self.env['absent.log'].create(value)
            
    @api.model
    def create(self, vals):
        res = super(HrAttendance, self).create(vals)
#         if res.is_absent == True or res.missed == True:
#             if res.employee_id.approve_manager:
#                 one_signal_values = {'employee_id': res.employee_id.approve_manager.id,
#                                      'contents': _('ATTENDANCE: %s created attendance.') % res.employee_id.name,
#                                      'headings': _('WB B2B : ATTENDANCE CREATED')}
#                 self.env['one.signal.notification.message'].create(one_signal_values)
        return res

    def write(self, vals):
        res = super(HrAttendance, self).write(vals)
#         if vals.get('check_out') and self.is_absent:
#             if self.employee_id.approve_manager:
#                 one_signal_values = {'employee_id': self.employee_id.approve_manager.id,
#                                      'contents': _('ATTENDANCE: %s created attendance.') % self.employee_id.name,
#                                      'headings': _('WB B2B : CREATED ATTENDANCE')}
#                 self.env['one.signal.notification.message'].create(one_signal_values)
        return res


class ChangeLateMinutesWizard(models.TransientModel):
    _name = "change.late.minutes.wizard"
    _description = "Change Late Minutes Wizard"

    late_minutes = fields.Float('Late Minutes')

    def change(self):
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids')), ('check_out', '!=', False), ('state', '!=', 'decline')]
            attendances = self.env['hr.attendance'].search(domain)
            if attendances:
                attendances.write({'late_minutes': self.late_minutes})
                self._cr.commit()
        return {'type': 'ir.actions.act_window_close'}
    

class ChangeEarlyOutMinutesWizard(models.TransientModel):
    _name = "change.early.out.minutes.wizard"
    _description = "Change Early Out Minutes Wizard"

    early_out_minutes = fields.Float('Early Out Minutes')

    def change(self):
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids')), ('check_out', '!=', False), ('state', '!=', 'decline')]
            attendances = self.env['hr.attendance'].search(domain)
            if attendances:
                attendances.write({'early_out_minutes': self.early_out_minutes})
                self._cr.commit()
        return {'type': 'ir.actions.act_window_close'}


class ChangeOtHourWizard(models.TransientModel):
    _name = "change.ot.hour.wizard"
    _description = "Change OT Hour Wizard"

    ot_hour = fields.Float('OT Hours')

    def change(self):
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids')), ('check_out', '!=', False), ('state', '!=', 'decline')]
            attendances = self.env['hr.attendance'].search(domain)
            if attendances:
                attendances.write({'ot_hour': self.ot_hour})
                self._cr.commit()
        return {'type': 'ir.actions.act_window_close'}


class ChangeWorkedHoursWizard(models.TransientModel):
    _name = "change.worked.hours.wizard"
    _description = "Change Worked Hours Wizard"

    worked_hours = fields.Float('Worked Hours')

    def change(self):
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids')), ('check_out', '!=', False), ('state', '!=', 'decline')]
            attendances = self.env['hr.attendance'].search(domain)
            if attendances:
                attendances.write({'worked_hours': self.worked_hours})
                self._cr.commit()
        return {'type': 'ir.actions.act_window_close'}
