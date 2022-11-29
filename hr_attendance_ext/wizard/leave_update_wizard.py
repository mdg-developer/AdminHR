# -*- coding: utf-8 -*-
# Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)

import time
from odoo import models, api, fields, _
from odoo.exceptions import Warning
from dateutil import parser
import logging
import math
import json
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from pytz import timezone, UTC
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.tools import format_datetime, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
from odoo.addons.hr_attendance_ext.models.hr_attendance import time_to_float
import time

class leave_update_wizard(models.TransientModel):
    _name = 'leave.update.wizard'
    
    company_id = fields.Many2one('res.company', string='Company', required=False) 
                                 #default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")
    department_id = fields.Many2one('hr.department', string='Department', domain="[('branch_id', '=', branch_id)]")
    employee_ids = fields.Many2many('hr.employee', string='Employee')    
    date_from = fields.Date('Date From', required=True, default=fields.Date.context_today)
    date_to = fields.Date('Date To', required=True, default=fields.Date.context_today)   

        
    @api.onchange('branch_id','department_id')
    def onchange_employee_only(self):
        """
        Make warehouse compatible with company
        """
        employee_obj = self.env['hr.employee']
        employee_ids = []
        
        if self.department_id:
            location_ids = employee_obj.search([('department_id', '=', self.department_id.id)])
            employee_ids = [p.id for p in location_ids] 
            return {
                  'domain':
                            {
                             'employee_ids': [('id', 'in', employee_ids)]
                             },
                  'value':
                        {
                        'employee_ids': False
                        }
                }
        elif self.branch_id:
            
            location_ids = employee_obj.search([('branch_id', '=', self.branch_id.id)])
            employee_ids = [p.id for p in location_ids]        
            return {
                      'domain':
                                {
                                 'employee_ids': [('id', 'in', employee_ids)]
                                 },
                      'value':
                            {
                            'employee_ids': False
                            }
                    }
        else:
            if self.company_id:
                location_ids = employee_obj.search([('company_id', '=', self.company_id.id)])
            else:
                location_ids = employee_obj.search([])
                
            employee_ids = [p.id for p in location_ids]        
            return {
                      'domain':
                                {
                                 'employee_ids': [('id', 'in', employee_ids)]
                                 },
                      'value':
                            {
                            'employee_ids': False
                            }
                    }
        def check_distinct_workhour(self,att):
            calendar = att.employee_id.resource_calendar_id
            tz = timezone(calendar.tz)
            check_in = att.check_in + timedelta(hours=+6,minutes=+30)#att.check_in.astimezone(tz)
            
            in_float = time_to_float(check_in)
            start_time_early = math.floor(in_float - 2) 
            start_time_late = math.floor(in_float + 2)        
            dayofweek = check_in.weekday()                
            day_period = in_float < 12 and 'morning' or 'afternoon'
    
            domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', calendar.id),
                      ('dayofweek', '=', str(dayofweek)), ('day_period', '=', day_period)]
            if calendar.two_weeks_calendar:
                week_type = int(math.floor((check_in.toordinal() - 1) / 7) % 2)
                domain += [('week_type', '=', str(week_type))]
    
            working_hours = self.env['resource.calendar.attendance'].search(domain)
            result = 2
            for wh in working_hours:
                hour_from = wh.hour_from + 0.000001
                hour_to = wh.hour_to + 0.000001
                in_diff = out_diff = 0
                if start_time_early < math.floor(wh.hour_from) < start_time_late:                
                    worked_hour = math.floor(hour_to - hour_from)
                    
                
            early_out = worked_hour - 2
            late_out = worked_hour + 2
            
            early_out_time = att.check_in + timedelta(hours=+early_out)
            late_out_time = att.check_in + timedelta(hours=+late_out) 
            return late_out_time
    
    def recalculate_leave(self,employee_ids):
        test = []
        for emp_id in employee_ids:
            end_date = self.date_to
            beg_date = self.date_from
            calendar = emp_id.resource_calendar_id
            tz = timezone(calendar.tz)
            leave_ids = self.env['hr.leave'].search([('employee_id','=',emp_id.id),('request_date_from','>=',self.date_from),('request_date_to','<=',self.date_to),('state','in',['validate','validate1'])])
            for leave in leave_ids:
                start_time = leave.date_from + timedelta(hours = -2)
                end_time = leave.date_to + timedelta(hours = 4)
                                    
                raw_date = leave.request_date_from
                raw_float_time = time_to_float(leave.date_from)            
                raw_day_period = raw_float_time < 12 and 'morning' or 'afternoon'
                date_start = tz.localize((fields.Datetime.to_datetime(raw_date)), is_dst=True).astimezone(tz=UTC)
                date_stop = tz.localize((datetime.combine(fields.Datetime.to_datetime(raw_date), datetime.max.time())), is_dst=True).astimezone(tz=UTC)
    
                dayofweek = raw_date.weekday()
                domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', calendar.id), ('dayofweek', '=', str(dayofweek))]
                if calendar.two_weeks_calendar:
                    week_type = int(math.floor((raw_date.toordinal() - 1) / 7) % 2)
                    domain += [('week_type', '=', str(week_type))]
    
                working_hours = self.env['resource.calendar.attendance'].search(domain)
                attendances = self.env['hr.attendance'].search([('employee_id','=',emp_id.id),('check_in','>=',start_time),('check_out','<=',end_time)])        
                for attendance_id in attendances:
                    test.append(attendance_id.id)
                    if leave.holiday_status_id.travel_leave == True:
                        attendance_id.write({'is_absent':False,'travel':True})
       
                    else:
                        attendance_id.write({'is_absent':False,'leave':True})
                    
                    if leave.number_of_days < 1:
                        self.compute_late_early(attendance_id, leave)
                    elif leave.number_of_days >=1 and attendance_id.late_minutes >0 or attendance_id.early_out_minutes >0:
                        attendance_id.write({'late_minutes':0.0,'early_out_minutes':0.0})
                        
                if not attendances:
                    attendances = self.env['hr.attendance'].search([('check_in', '>=', leave.date_from),
                                                        ('check_in', '<', leave.date_to),
                                                        ('employee_id', '=', emp_id.id)], order='check_in desc', limit=1) 
                    if not attendances:
                        attendances = self.env['hr.attendance'].search([('check_in', '>=', date_start),
                                                        ('check_in', '<', date_stop),
                                                        ('employee_id', '=', emp_id.id)], order='check_in desc', limit=1)
                    if leave.holiday_status_id.travel_leave == True and attendances.check_in:
                        attendances.write({'is_absent':False,'missed':False,'travel':True})
                    elif leave and attendances.check_in:
                        attendances.write({'is_absent': False, 'missed': False, 'leave': True})
                    elif attendances.check_out:
                        attendances.write({'is_absent':False,'leave':True}) 
                        
                    if attendances:
                        if leave.number_of_days < 1:
                            self.compute_late_early(attendances, leave)
                        elif leave.number_of_days >=1 and attendances.late_minutes >0 or attendances.early_out_minutes >0:
                            attendances.write({'late_minutes':0.0,'early_out_minutes':0.0})      
                print(test)
                
    def compute_late_early(self,att,leave):
        
        #att.late_minutes = att.early_out_minutes = att.ot_hour = att.early_ot_hour = 0

        if att.check_in and att.check_out:
            calendar = att.employee_id.resource_calendar_id
            tz = timezone(calendar.tz)
            check_in = att.check_in + timedelta(hours=+6,minutes=+30)#att.check_in.astimezone(tz)
            check_out = att.check_out + timedelta(hours=+6,minutes=+30)#att.check_out.astimezone(tz)
            in_float = time_to_float(check_in)
            out_float = time_to_float(check_out)
            leave_start_float = time_to_float(leave.date_from + timedelta(hours=+6,minutes=+30))
            dayofweek = check_in.weekday()                
            day_period = in_float < 12 and 'morning' or 'afternoon'
            leave_period = leave_start_float < 12 and 'morning' or 'afternoon'
            
            domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', calendar.id),
                      ('dayofweek', '=', str(dayofweek)), ('day_period', '=', day_period)]
            if calendar.two_weeks_calendar:
                week_type = int(math.floor((check_in.toordinal() - 1) / 7) % 2)
                domain += [('week_type', '=', str(week_type))]

            working_hours = self.env['resource.calendar.attendance'].search(domain)
            for wh in working_hours:
                hour_from = wh.hour_from + 0.000001
                hour_to = wh.hour_to + 0.000001
                
                if leave_period == 'afternoon':
                    hour_to = wh.lunch_from + 0.000001 if wh.lunch_from >= 0 else leave_start_float
                else:
                    hour_from = wh.lunch_to + 0.000001 if wh.lunch_to >= 0 else leave_start_float
                
                in_diff = out_diff = 0
                if round(wh.hour_from) == 0:
                    out_diff = hour_to - out_float
                elif round(wh.hour_to) == 24:
                    in_diff = in_float - hour_from
                else:
                    in_diff = in_float - hour_from
                    out_diff = hour_to - out_float

                att.late_minutes = in_diff > 0 and in_diff or 0                
                att.early_out_minutes = out_diff > 0 and out_diff or 0
                
                    
    def run_update(self):
        test = []
        if len(self.employee_ids) > 0:
            self.recalculate_leave(self.employee_ids)
        else:            
            domain = [('company_id','=',self.env.company)]
            if self.branch_id:
                domain +=  [('branch_id','=',self.branch_id.id)]
            if self.department_id:
                domain +=  [('department_id','=',self.department_id.id)]
            
            employee_ids = self.env['hr.employee'].search(domain)        
            self.recalculate_leave(employee_ids)
                
