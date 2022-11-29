import math
from odoo import api, models, fields, _
from odoo.tools import date_utils
from odoo.tools.misc import format_date
from pytz import timezone, UTC
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from calendar import monthrange
from odoo.addons.hr_attendance_ext.models.hr_attendance import time_to_float
from odoo.addons.hr_payroll_ext.reports.report_payroll_wizard import MONTH_SELECTION
from odoo.tools import float_compare, float_is_zero
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
import pytz

import calendar


from odoo.osv import expression


def float_to_hr_min(value):
    if value < 0:
        value = abs(value)

    hour = int(value)
    minute = round((value % 1) * 60)

    if minute == 60:
        minute = 0
        hour = hour + 1
    return hour, minute

def float_to_time(value):
    if value < 0:
        value = abs(value)

    hour = int(value)
    minute = round((value % 1) * 60)

    if minute == 60:
        minute = 0
        hour = hour + 1
    return time(hour, minute)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    days_of_month = fields.Integer('Days of Month', compute='get_days_of_month', store=True)
    previous_income = fields.Float('Previous Income', compute='_compute_previous_amount', store=True)
    previous_tax_paid = fields.Float('Previous Tax Paid', compute='_compute_previous_amount', store=True)
    remaining_months = fields.Integer('Remaining Months', compute='_compute_previous_amount', store=True)
    total_months = fields.Integer('Total Months', compute='_compute_previous_amount', store=True)
    sunday_unpaid = fields.Integer('Sunday Unpaid', compute='_compute_previous_amount', store=False)
    half_month_day = fields.Integer('Half Month Join', compute='_compute_previous_amount', store=False)
    service_year = fields.Integer('Service Year', compute='_get_service_year')
    journal_id = fields.Many2one('account.journal', 'Salary Journal', domain="[('company_id', '=', company_id)]")
    misc_journal_id = fields.Many2one('account.journal', 'Misc Journal', related='struct_id.misc_journal_id', domain="[('company_id', '=', company_id)]", store=True)
    misc_move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, store=True, copy=False)
    gross_wage = fields.Monetary(compute='_compute_basic_net')
    logistics_journal_id = fields.Many2one('account.journal', 'Logistics Commission Journal', related='struct_id.logistics_commission_journal', domain="[('company_id', '=', company_id)]", store=True)
    logistics_move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, store=True, copy=False)

    def _compute_basic_net(self):
        for payslip in self:
            payslip.basic_wage = payslip._get_salary_line_total('BASIC')
            payslip.net_wage = payslip._get_salary_line_total('NET')
            payslip.gross_wage = payslip._get_salary_line_total('GROSS')

    @api.depends('date_to')
    def _get_service_year(self):
        for payslip in self:
            payslip.service_year = 0
            if payslip.employee_id.joining_date:
                duration = relativedelta(payslip.date_to, payslip.employee_id.joining_date)
                years = duration.years or 0
                payslip.service_year = years
    
    def _get_gz_holiday_leave(self,employee_id,beg_date,end_date,date_from,date_to):
        holiday_count = 0
        before_holiday_count = 0
        after_holiday_count = 0  
        holiday_list = []
        beg_saturday = datetime.strptime(beg_date + '00:00:00', '%Y-%m-%d %H:%M:%S').date()
        end_monday  =datetime.strptime(end_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S').date()    
        beg_holiday = datetime.strptime(beg_date + '00:00:00', '%Y-%m-%d %H:%M:%S').date() #+ timedelta(days=-1)
        end_holiday = datetime.strptime(end_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S').date() # + timedelta(days=1)
        before_saturday = after_sunday = False
        before = after = 1
        while before != 0:
            public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_holiday),
                                                                          ('line_id.company_id', '=', employee_id.company_id.id)], order='id desc', limit=1)
                
                
            if not public_holiday:
                public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_holiday),
                                                                          ('line_id.company_id', '=', False)], order='id desc', limit=1)
            if public_holiday:
                holiday_list.append(public_holiday.date)    
                beg_holiday = beg_holiday + timedelta(days=-1)
                before_holiday_count +=1 
            else:
                leave = self.env['hr.leave'].search([('request_date_from','=',beg_holiday),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1)
                print(str(beg_holiday))
                if leave :
                    if  beg_holiday != beg_saturday:
                        before_saturday = True
                        #before_holiday_count +=1
                        beg_holiday = beg_holiday + timedelta(days=-1)
                        before = 0
                       
                    else:
                        before = 0
                else:
                    before = 0
                if before_saturday == True:
                    holiday_count = before_holiday_count   
        while after != 0:
            public_holiday = self.env['public.holidays.line'].search([('date', '=', end_holiday),
                                                                          ('line_id.company_id', '=', employee_id.company_id.id)], order='id desc', limit=1)
                
                
            if not public_holiday:
                public_holiday = self.env['public.holidays.line'].search([('date', '=', end_holiday),
                                                                          ('line_id.company_id', '=', False)], order='id desc', limit=1)
            if public_holiday:
                holiday_list.append(public_holiday.date)    
                end_holiday = end_holiday + timedelta(days=1)
                after_holiday_count +=1 
            else:
                leave = self.env['hr.leave'].search([('request_date_from','=',end_holiday),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1)
                if leave:
                    if end_holiday != end_monday:
                        after_sunday = True
                        #after_holiday_count +=1
                        end_holiday = end_holiday + timedelta(days=1)
                        after = 0
                    else:
                        after = 0
                else:
                    after = 0
                if after_sunday == True:
                    holiday_count += after_holiday_count + 1
        
        leave_start = self.env['hr.leave'].search([('request_date_from','=',date_from),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1)
        leave_end = self.env['hr.leave'].search([('request_date_from','=',date_to),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1) 
        if leave_start and leave_end:
            public_holidays = self.env['public.holidays.line'].search([('date', '>=', date_from),('date', '<=', date_to),
                                                                          ('line_id.company_id', '=', employee_id.company_id.id)], order='id desc')
            if not public_holidays:
                public_holidays = self.env['public.holidays.line'].search([('date', '>=', date_from),('date', '<=', date_to),
                                                                          ('line_id.company_id', '=', False)], order='id desc')
            for holiday in public_holidays:
                if holiday.date not in holiday_list:
                    dayofweek = holiday.date.weekday()
                    print(dayofweek)
                    if dayofweek != 6 and dayofweek != 5 and dayofweek != 0:
                        holiday_list.append(holiday.date)
                        holiday_count += 1
        return holiday_count
                    
    def _get_sunday_list(self,employee_id,date_from,date_to):
        end_date = date_to
        beg_date = date_from
        sunday_list = []
        sunday_count = 0
        while beg_date <= end_date:
            dayofweek = beg_date.weekday()
            if dayofweek == 6:
                saturday = beg_date + timedelta(days=-1)
                monday = beg_date + timedelta(days=1)                                
                res ={'Saturday': saturday.strftime("%Y-%m-%d "),'Sunday':beg_date.strftime("%Y-%m-%d "),'Monday':monday.strftime("%Y-%m-%d ")}
                sunday_list.append(res)
            beg_date = beg_date + timedelta(days=1)
            
        for sunday in sunday_list: 
            sunday_flg = False           
            sunday_leave = self.env['hr.leave'].search([('request_date_from','=',sunday['Saturday']),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1)
            monday_leave = self.env['hr.leave'].search([('request_date_to','=',sunday['Monday']),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1)
            if sunday_leave and monday_leave:
                if employee_id.resource_calendar_id.no_holidays == False:
                    sunday_count += 1
                    sunday_flg = True
                
            if not sunday_leave or not monday_leave:
                gz_count = self._get_gz_holiday_leave(employee_id, sunday['Saturday'], sunday['Monday'],date_from,date_to)
                print("gz_count>>>>>>",gz_count)
                if gz_count > 0:
                    sunday_count += gz_count #+ 1
                    sunday_flg = True
                    continue 
            if sunday_flg == True:
                continue        
            leave = self.env['hr.leave'].search([('request_date_from','<=',sunday['Saturday']),('request_date_to','>=',sunday['Monday']),('holiday_status_id','=',4),('state','in',['validate','validate1']),
                                                 ('employee_id','=',employee_id.id)],limit=1)
            if leave:
                sunday_count += 1
        return sunday_count 
           
    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_previous_amount(self):
        for slip in self:
            prev_income = 0#slip.employee_id.salary_total
            prev_tax_paid = 0#slip.employee_id.tax_paid
            remaining_months = 0
            total_months = 12
            today = fields.Date.today()
            fiscal_year = self.env['hr.fiscal.year'].search([('date_from', '<=', slip.date_to),
                                                                  ('date_to', '>=', slip.date_to),
                                                                  ('company_id','=',slip.employee_id.company_id.id)])
            print("_compute_previous_amount>>>",fiscal_year,slip.date_to)
            if fiscal_year:
                remaining_months = relativedelta(fiscal_year.date_to, slip.date_to).months
                if slip.employee_id.joining_date and fiscal_year.date_from < slip.employee_id.joining_date < fiscal_year.date_to:
                    prev_income = slip.employee_id.salary_total
                    prev_tax_paid = slip.employee_id.tax_paid
                if slip.employee_id.joining_date and slip.employee_id.joining_date > fiscal_year.date_from:
                    total_months = 12 - relativedelta(slip.employee_id.joining_date, fiscal_year.date_from).months
                payslips = self.env['hr.payslip'].sudo().search([('employee_id', '=', slip.employee_id.id),
                                                          ('date_to', '>=', fiscal_year.date_from),
                                                          ('date_to', '<=', fiscal_year.date_to),
                                                          ('state', 'not in', ('draft', 'cancel'))])
                for pay in payslips:
                    slipline_obj = self.env['hr.payslip.line']
                    basic = slipline_obj.sudo().search([('slip_id', '=', pay.id), ('code', '=', 'BASIC')])
                    # deductions = slipline_obj.search([('slip_id', '=', pay.id), ('code', 'in', ('UNPAID', 'SSB'))])
                    deductions = slipline_obj.sudo().search([('slip_id', '=', pay.id), ('code', '=', 'D03')])
                    tax_paid = slipline_obj.sudo().search([('slip_id', '=', pay.id), ('code', '=', 'ICT')])
                    absents = slipline_obj.sudo().search([('slip_id','=',pay.id),('code','=','ABSENCE')])
                    prev_income += basic and basic.total or 0
                    prev_income -= sum([abs(ded.total) for ded in deductions])                    
                    prev_income -= sum([abs(dedabs.total) for dedabs in absents])
                    prev_tax_paid += tax_paid and tax_paid.total or 0
                    
            sunday_unpaid = self._get_sunday_list(slip.employee_id, slip.date_from, slip.date_to)
            slip.remaining_months = remaining_months
            slip.previous_income = prev_income
            slip.previous_tax_paid = prev_tax_paid
            slip.total_months = total_months
            slip.sunday_unpaid = 0#sunday_unpaid
            slip.half_month_day = 0
            if slip.employee_id.joining_date and (datetime.strptime(str(slip.employee_id.joining_date), '%Y-%m-%d').strftime("%Y-%m") == datetime.strptime(str(slip.date_from), '%Y-%m-%d').strftime("%Y-%m")):
                delta = slip.date_to - slip.employee_id.joining_date
                slip.half_month_day =  delta.days + 1
            elif slip.employee_id.resign_date and (datetime.strptime(str(slip.employee_id.resign_date), '%Y-%m-%d').strftime("%Y-%m") == datetime.strptime(str(slip.date_from), '%Y-%m-%d').strftime("%Y-%m")): 
                delta = slip.employee_id.resign_date - slip.date_from
                slip.half_month_day =  delta.days + 1
                remaining_months = relativedelta(slip.date_to,slip.employee_id.resign_date).months
                slip.total_months = relativedelta(slip.date_to,fiscal_year.date_from).months
                slip.remaining_months = remaining_months
            
            print("sunday_unpaid>>>",sunday_unpaid)

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    year = fields.Selection(selection='_get_selection', string='Year', default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', default=lambda x: str(datetime.now().month))

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_from = date(year=int(self.year), month=int(self.month), day=1)
            self.date_to = date(year=int(self.year), month=int(self.month), day=monthrange(int(self.year), int(self.month))[1])

    @api.depends('date_from')
    def get_days_of_month(self):
        for slip in self:
            if slip.date_from:
                slip.days_of_month = monthrange(slip.date_to.year, slip.date_to.month)[1]
            else:
                slip.days_of_month = 0

    def _get_work_hours(self, date, calendar, dayofweek):
        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', calendar.id), ('dayofweek', '=', str(dayofweek))]
        if calendar.two_weeks_calendar:
            week_type = int(math.floor((date.toordinal() - 1) / 7) % 2)
            domain += [('week_type', '=', str(week_type))]
        work_hours = self.env['resource.calendar.attendance'].search(domain)
        return work_hours
    
    def check_leave(self,emp,beg_date,hour_from,hour_to):
        tz = timezone(emp.resource_calendar_id.tz or 'Asia/Yangon')        
        date_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(beg_date), float_to_time(hour_from)), is_dst=True).astimezone(tz=UTC)
        date_stop = tz.localize(datetime.combine(fields.Datetime.to_datetime(beg_date), float_to_time(hour_to)), is_dst=True).astimezone(tz=UTC)
        ratio = 1
        print(beg_date)
        print(date_start)
        print(date_stop)
        leave = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id),
                                                 ('state', '=', 'validate'), '|',
                                                 ('date_from', '=', date_start),
                                                 ('date_to', '=', date_stop)],
                                                order='date_from asc')
        if leave:
            if leave.number_of_days >= 1:
                ratio = 3
            else: 
                ratio = 2
        return ratio
        
                                    
    def _get_input_lines(self):
        res = []
        self.ensure_one()
        struct = self.struct_id
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        calendar = self.employee_id.resource_calendar_id
        tz = timezone(calendar.tz)
        eloan_amount = tloan_amount = 0
        commission_amount = 0
        input_type_obj = self.env['hr.payslip.input.type']
        other_allowance_input = self.env.ref('hr_payroll_ext.input_type_other_allowance')
        other_deduction_input = self.env.ref('hr_payroll_ext.input_type_other_deduction')
        logistics_commission_input = self.env.ref('hr_payroll_ext.input_type_sales_commission')
        tmp_duty_ids = []
        # DEDUCTION
        deduction = self.env['hr.deduction'].sudo().search([('employee_id', '=', employee.id),
                                                            ('effective_date', '<=', date_to), '|',
                                                            ('end_date', '=', False),
                                                            ('end_date', '>=', date_to)])
        if deduction:
            for ded in deduction:
                if ded.effective_type == 'one_time' and (ded.effective_date.month != date_from.month or ded.effective_date.year != date_from.year):
                    continue
                elif ded.effective_type == 'yearly' and ded.effective_date.month != date_from.month:
                    continue
                if ded.deduction_config_id.code in ('D01', 'D02'):
                    input_type = input_type_obj.search([('code', '=', ded.deduction_config_id.code)])
                    if input_type:
                        existing_ded = next((input for input in res if input["input_type_id"] == input_type.id), False)
                        if existing_ded:
                            existing_ded.update({'amount': existing_ded['amount'] + ded.amount})
                        else:
                            res.append({'input_type_id': input_type.id,
                                        'amount': ded.amount})
                else:

                    res.append({'input_type_id': other_deduction_input.id,
                               'amount': ded.amount})
                    
        # ALLOWANCE
        allowance = self.env['hr.allowance'].sudo().search([('employee_id', '=', employee.id),
                                                            ('effective_date', '<=', date_to), '|',
                                                            ('end_date', '=', False),
                                                            ('end_date', '>=', date_to)])

        if allowance:
            for alw in allowance:
                if alw.effective_type == 'one_time' and (alw.effective_date.month != date_from.month or alw.effective_date.year != date_from.year):
                    continue
                elif alw.effective_type == 'yearly' and alw.effective_date.month != date_from.month:
                    continue
                if alw.allowance_config_id.code in ('A01', 'A02', 'A03', 'A04', 'A05', 'A06'):
                    input_type = input_type_obj.search([('code', '=', alw.allowance_config_id.code)])
                    if input_type:
                        existing_alw = next((input for input in res if input["input_type_id"] == input_type.id), False)
                        if existing_alw:
                            existing_alw.update({'amount': existing_alw['amount'] + alw.amount})
                        else:
                            res.append({'input_type_id': input_type.id,
                                        'amount': alw.amount})
                else:
                    res.append({'input_type_id': other_allowance_input.id,
                               'amount': alw.amount})

        # LOGISTICS COMMISSION
        logistics_commission = self.env['hr.logistics.commission'].sudo().search([('employee_id', '=', employee.id),
                                                                ('from_datetime', '>=', str(date_from) + ' 00:00:00'),
                                                                ('from_datetime', '<=', str(date_from) + ' 23:59:59'),
                                                                ('to_datetime', '>=', str(date_to) + ' 00:00:00'),
                                                                ('to_datetime', '<=', str(date_to) + ' 23:59:59')])

        if logistics_commission:
            for rec in logistics_commission:
                commission_amount += rec.commission
            if commission_amount:
                res.append({'input_type_id': logistics_commission_input.id,
                            'amount': commission_amount})

        # LOAN
        loan_line_obj = self.env['hr.loan.line'].sudo()
        loans = loan_line_obj.search([('employee_id', '=', employee.id),
                                      ('date', '>=', date_from),
                                      ('date', '<=', date_to),
                                      ('paid', '=', False),
                                      ('state','!=','clear'),
                                      ('loan_id.state', 'in', ('verify','approve'))])

        eloan_ids = tloan_ids = loan_line_obj
        print("eloan_ids>>>>",eloan_ids)
        for loan in loans:
            if loan.loan_id.type == 'training':
                eloan_amount += loan.amount
                eloan_ids += loan
            elif loan.loan_id.type == 'others':
                tloan_amount += loan.amount
                tloan_ids += loan
        
        
        if eloan_amount:
            print("Eloan " + str(eloan_ids))
            print("Eloan ids " + str(eloan_ids.ids))
            res.append({'input_type_id': self.env.ref('hr_payroll_ext.other_input_type_loan_entitlement').id,
                        'loan_line_ids': [(6, 0, eloan_ids.ids)],
                        'amount': eloan_amount})
        if tloan_amount:
            print("Tloan " + str(tloan_ids))
            print("Tloan ids " + str(tloan_ids.ids))
            res.append({'input_type_id': self.env.ref('hr_payroll_ext.other_input_type_loan_training').id,
                        'loan_line_ids': [(6, 0, tloan_ids.ids)],
                        'amount': tloan_amount})
        
        # INSURANCE
        insurance_line_obj = self.env['hr.insurance.line'].sudo()
        insurance = insurance_line_obj.search([('employee_id', '=', employee.id),
                                      ('date', '>=', date_from),
                                      ('date', '<=', date_to),
                                      ('paid', '!=', True)])
        insurance_ids = insurance_line_obj.browse([])
        insurance_amount = 0.0
        for i in insurance:
            insurance_amount += i.amount
            insurance_ids += i
        if insurance_amount:
            res.append({'input_type_id': self.env.ref('hr_payroll_ext.other_input_type_insurance_deduction').id,
                        'insurance_line_ids': [(6, 0, insurance_ids.ids)],
                        'amount': insurance_amount})

        # OT
        #duty_structs = self.env['hr.payroll.structure'].search([('name', 'in', ('ST05', 'ST06', 'ST07', 'ST08'))])
        duty_structs = self.env['hr.payroll.structure'].search([('shift', '=', True)]) 
        daily_struct = self.env.ref('hr_payroll_ext.structure_daily_wages')

        ot_duty = late = 0        
        start_time = (tz.localize(datetime(year=date_from.year, month=date_from.month, day=date_from.day), is_dst=None)).astimezone(UTC)
        end_time = (tz.localize(datetime(year=date_to.year, month=date_to.month, day=date_to.day), is_dst=None)).astimezone(UTC) + timedelta(days=1)
       
        attendances = self.env['hr.attendance'].search([('employee_id', '=', employee.id),
                                                        ('check_in', '>=', start_time),
                                                        ('check_in', '<', end_time),('no_worked_day', '=',False),
                                                        ('is_absent','=',False),('missed','=',False),#('leave','=',False),
                                                        ('state', 'in', ('approve', 'verify'))], order='check_in asc')
        for att in attendances:
            if att.id in [119695]:#[153485,153486,153501,153502,153504,153488,153489]:
                print("test",att.id)
            check_in = att.check_in.astimezone(tz)
            check_out = att.check_out and att.check_out.astimezone(tz) or False            
            begin_date = att.check_in + timedelta(hours=+6,minutes=+30)
            print("begin_date.date()>>>",begin_date.date())            
            dayofweek = begin_date.weekday()
            oneday_off = False
            public_holiday = self.env['public.holidays.line'].search([('date', '=', begin_date.date()),
                                                                      ('line_id.company_id', '=', att.employee_id.company_id.id)], order='id desc', limit=1)
                        
            if not public_holiday:
                public_holiday = self.env['public.holidays.line'].search([('date', '=', begin_date.date()),
                                                                          ('line_id.company_id', '=', False)], order='id desc', limit=1)
            
            working_hours = self._get_work_hours(begin_date.date(), calendar, dayofweek)
            #add logic special calculation for ot duty on one day off and no holiday shift 
            if not public_holiday:                
#                 if (self.employee_id.resource_calendar_id.one_day_off == True and dayofweek==6):
#                     dayofweek = 1 #change one day off disable as all one day off will closed sunday
                if self.employee_id.resource_calendar_id.one_day_off == True and not working_hours:
                    oneday_off = True
                    continue
                elif self.employee_id.resource_calendar_id.no_holidays == True and dayofweek==6:
                    continue                
            if (self.employee_id.resource_calendar_id.one_day_off == True and self.employee_id.resource_calendar_id.hours_per_day > 11) or (self.employee_id.resource_calendar_id.no_holidays == True and self.employee_id.resource_calendar_id.hours_per_day > 11):
                if not ((public_holiday and public_holiday.type == 'holiday') or (not public_holiday and dayofweek == 6)):
                    if struct in duty_structs:
                        dayofweek = begin_date.weekday()
                        work_hours = self._get_work_hours(begin_date.date(), calendar, dayofweek)
                        if work_hours:
                            if len(work_hours) == 1:
                                work_hour = work_hours.hour_to - work_hours.hour_from
                                take_leave = self.check_leave(self.employee_id, begin_date.date(), work_hours.hour_from, work_hours.hour_to)
                                if take_leave == 3:
                                    continue
                                if work_hour > 8 and check_in and check_out:
                                    ot_duty += (work_hour - 8) / take_leave
                                    tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':work_hour - 8})
                                elif work_hour > 4 and check_in and check_out:
                                    ot_duty += (work_hour - 4) / take_leave
                                    tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':work_hour - 4})
                            elif len(work_hours) == 2:
                                work_hour = 0 
                                for wh in work_hours:
                                    work_hour += wh.hour_to - wh.hour_from 
                                if work_hour > 8 and check_in and check_out:                               
                                    ot_duty += 2
                                
                                tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':2})
                    elif struct == daily_struct:
                        late += math.ceil(att.late_minutes)
                continue
            #end ot duty logic
                
            #public_holiday = self.env['public.holidays.line'].search([('date', '=', begin_date.date())])
            print("check_in.date()>>>",check_in.date())
            print("att.check_in>>>",att.check_in)
            print("att.check_in>>>",att.check_in.date())
            if not ((public_holiday and public_holiday.type == 'holiday') or (not public_holiday and dayofweek == 6 )):
                if struct in duty_structs:
                    dayofweek = begin_date.weekday()
                    work_hours = self._get_work_hours(check_in, calendar, dayofweek)
                    if work_hours:
                        if check_out and round(time_to_float(check_out)) == 24:
                            start_work_hour = work_hours.filtered(lambda wh: round(wh.hour_to) == 24)
                            next_day = check_in + timedelta(days=1)
                            next_work_hours = self._get_work_hours(next_day, calendar, next_day.weekday())
                            end_work_hour = next_work_hours.filtered(lambda wh: round(wh.hour_from) == 0)
                            next_start = (tz.localize(datetime(year=next_day.year, month=next_day.month, day=next_day.day), is_dst=None)).astimezone(UTC)
                            next_end = next_start + timedelta(days=1, seconds=-1)
                            next_attend = self.env['hr.attendance'].search([('employee_id', '=', employee.id),
                                                                            ('check_in', '>=', next_start),
                                                                            ('check_in', '<', next_end),
                                                                            ('state', 'in', ('approve', 'verify'))],
                                                                           order='check_in asc', limit=1)
                            
                            if start_work_hour and end_work_hour and next_attend:
                                work_hour = (24 + end_work_hour.hour_to) - start_work_hour.hour_from
                                print("work_hour>>",round(time_to_float(next_attend.check_in.astimezone(tz))))
                                print("work_hour>>",next_attend.check_in.astimezone(tz))
                                if work_hour > 8 and round(time_to_float(next_attend.check_in.astimezone(tz))) == 0:
                                    ot_duty += work_hour - 8
                                    tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':work_hour - 8})
                                elif work_hour > 4:
                                    ot_duty += work_hour - 4
                                    tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':work_hour - 4})
                        elif round(time_to_float(check_in)) == 0:
                            pass
                        else:
                            if len(work_hours) == 1:
                                work_hour = work_hours.hour_to - work_hours.hour_from
                                if work_hour > 8 and check_out:
                                    ot_duty += work_hour - 8
                                    tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':work_hour - 8})
                                elif (work_hour/2) > 4 and check_out:
                                    ot_duty += work_hour - 4
                                    tmp_duty_ids.append({'id':att.id,'time':begin_date.date(),'hour':work_hour - 4})
                    else:
                        average_hours_per_day = round(calendar.hours_per_day)
                        ot_duty += average_hours_per_day - 8

                elif struct == daily_struct:
                    late += math.ceil(att.late_minutes)

        if ot_duty:
            print("tmp_duty_ids>>",tmp_duty_ids)
            res.append({'input_type_id': self.env.ref('hr_payroll_ext.other_input_type_ot_duty').id,
                        'amount': ot_duty})
        if late:
            res.append({'input_type_id': self.env.ref('hr_payroll_ext.other_input_type_late').id,
                        'amount': late})
        return res

    def _get_new_input_lines(self):
        input_line_values = self._get_input_lines()
        input_lines = self.input_line_ids.browse([])
        for r in input_line_values:
            input_lines |= input_lines.new(r)
        return input_lines
    
    def _get_late_early_day_lines(self):
        workentry_type = self.env['hr.work.entry.type'].search([('code','=','EL')],limit=1)
        calendar = self.employee_id.resource_calendar_id
        tz = timezone(calendar.tz)

        number_of_late_days = number_of_late_hours = 0.0
        date_start = tz.localize((fields.Datetime.to_datetime(self.date_from)).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
        date_stop = tz.localize((fields.Datetime.to_datetime(self.date_to + timedelta(days=1))).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)

        late_early_line = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                    ('check_in', '>=', date_start),
                                                    ('check_in', '<', date_stop),                                                    
                                                    ('state', '=', 'approve'),'|',('late_minutes','>',0),('early_out_minutes','>',0)],
                                                   order='check_in asc')
        print("late_early_line>>>",len(late_early_line))
        print("late_early_line id>>>",late_early_line)
        for deduct in late_early_line:
            if deduct.late_minutes > 0:
                number_of_late_hours += round(deduct.late_minutes,2)
            if deduct.early_out_minutes > 0:
                number_of_late_hours += round(deduct.early_out_minutes,2)
        
        if workentry_type and number_of_late_hours:
            delta = self.date_to - self.date_from
            day_months = delta.days + 1
            hours = int(number_of_late_hours)
            minutes = round((number_of_late_hours % 1) * 60) #(number_of_late_hours * 60) % 60
            #number_of_late_hours = hours + minutes
            if day_months > 27:
                one_hour_rate = (self.contract_id.wage / day_months) / 8
            else:
                one_hour_rate = self.contract_id.ot_duty_per_hour

            if self.contract_id.ot_duty_per_hour > 0:            
                #paid_amount = one_hour_rate * number_of_late_hours
                paid_amount = (one_hour_rate * hours) + ((one_hour_rate / 60) * minutes)
            else:
                paid_amount = 0
            return {'sequence': workentry_type.sequence,
                    'work_entry_type_id': workentry_type.id,
                    'number_of_days': number_of_late_days,
                    'number_of_hours': number_of_late_hours,
                    'amount': paid_amount,
                    }
        return {}
    def _get_absent_day_lines(self):
        absence_type = self.env.ref('hr_payroll_ext.work_entry_type_absence')
        calendar = self.employee_id.resource_calendar_id
        tz = timezone(calendar.tz)

        number_of_absent_days = number_of_absent_hours = 0
        date_start = tz.localize((fields.Datetime.to_datetime(self.date_from)).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
        date_stop = tz.localize((fields.Datetime.to_datetime(self.date_to + timedelta(days=1))).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)

        absence = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                    ('check_in', '>=', date_start),
                                                    ('check_in', '<', date_stop),
                                                    ('is_absent', '=', True),
                                                    ('state', '=', 'approve')],
                                                   order='check_in asc')
        for abc in absence:
            leave = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id),
                                                 ('state', '=', 'validate'), '|',
                                                 ('date_from', '=', abc.check_in),
                                                 ('date_to', '=', abc.check_out)],
                                                order='date_from asc')
            if not leave:
                if abc.check_out and abc.check_in:
                    diff_hours = abc.check_out - abc.check_in
                    absent_hours = diff_hours.seconds / 3600
                    if absent_hours > 8:
                        number_of_absent_days += 1
                    else:
                        number_of_absent_days += 0.5
                    number_of_absent_hours += absent_hours

        if number_of_absent_days and number_of_absent_hours:
            paid_amount = (((self.contract_id.wage * 12) / 52) / 48)
            return {'sequence': absence_type.sequence,
                    'work_entry_type_id': absence_type.id,
                    'number_of_days': number_of_absent_days,
                    'number_of_hours': number_of_absent_hours,
                    'amount': number_of_absent_hours * paid_amount,
                    }
        return {}

    def _get_fp_missed_lines(self):
        
        absence_type = self.env.ref('hr_payroll_ext.work_entry_type_fp_missed')
        calendar = self.employee_id.resource_calendar_id
        tz = timezone(calendar.tz)

        number_of_absent_days = number_of_absent_hours = 0
        date_start = tz.localize((fields.Datetime.to_datetime(self.date_from)).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
        date_stop = tz.localize((fields.Datetime.to_datetime(self.date_to + timedelta(days=1))).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
        # import pdb
        # pdb.set_trace()
        absences = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                    ('check_in', '>=', date_start),
                                                    ('check_in', '<', date_stop),
                                                    ('missed', '=', True),
                                                    ('state', '=', 'approve')],
                                                   order='check_in asc')
        for absence in absences:
            beg_date = absence.check_in + timedelta(hours=+6, minutes=+30)
            public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date.date()),
                                                                      ('line_id.company_id', '=', absence.employee_id.company_id.id)],
                                                                     order='id desc', limit=1)

            if not public_holiday:
                public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date.date()),
                                                                          ('line_id.company_id', '=', False)],
                                                                         order='id desc', limit=1)
            if self.employee_id.resource_calendar_id.hours_per_day <= 9 and self.employee_id.resource_calendar_id.holiday == True:
                dayofweek = beg_date.weekday()
                if dayofweek == 6:
                    continue

            if not public_holiday:
                number_of_absent_days += 1#len(absence)
        
        return {'sequence': absence_type.sequence,
                'work_entry_type_id': absence_type.id,
                'number_of_days': number_of_absent_days,
                'number_of_hours': number_of_absent_hours,
                
                }

    def _get_ot_hours(self, attendances, ot_responses):
        ot_hours = 0
        public_holiday = False
        for att in attendances:
            if att.check_out:
                ehr, emin = float_to_hr_min(round(att.early_ot_hour,2))
                lhr, lmin = float_to_hr_min(round(att.ot_hour,2))

                regular_checkin = att.check_in + timedelta(hours=ehr, minutes=emin)
                regular_checkout = att.check_out - timedelta(hours=lhr, minutes=lmin)
                early_ot_responses = ot_responses.filtered(lambda ot: ot.start_date - timedelta(hours=+2) < att.check_in < ot.end_date) #and ot.end_date < regular_checkout)
                #late_ot_responses = ot_responses.filtered(lambda ot: ot.start_date > regular_checkin and ot.end_date > regular_checkout)
                late_ot_responses = ot_responses.filtered(lambda ot: ot.start_date < regular_checkout < ot.end_date + timedelta(hours=+2))

                if early_ot_responses:                    
                    #print(att.check_in.date())
#                     if att.check_in.date() == early_ot_responses[0].start_date.date():
#                         early_start = max(att.check_in, early_ot_responses[0].start_date)
#                     else:
#                         early_start = min(att.check_in, early_ot_responses[0].start_date)
                    early_start = max(att.check_in, early_ot_responses[0].start_date)
                    early_end = min(att.check_out, early_ot_responses[0].end_date)
                    if early_start < early_end:
                        eot_diff = round((early_end - early_start).seconds / 3600, 2)
                        ot_hours += int(eot_diff) + 0.5 if round(eot_diff % 1, 2) >= 0.5 else int(eot_diff)
                        print("early_ot_responses>>>>>",early_start,early_end,eot_diff,ot_hours)
                if late_ot_responses:
                    late_start = max(att.check_in, late_ot_responses[0].start_date)
                    late_end = min(att.check_out, late_ot_responses[0].end_date)
                    print("late_ot_responses>>>>>",late_start,late_end)
                    if late_start < late_end:
                        lot_diff = round((late_end - late_start).seconds / 3600, 2)
                    else:
                        lot_diff = 0
                    late_checkin = att.check_in + timedelta(hours=+6, minutes=+30)
                    beg_date = late_checkin.date()
                    dayofweek = beg_date.weekday()
                    public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date),
                                                                              ('line_id.company_id', '=',
                                                                               att.employee_id.company_id.id)], order='id desc',
                                                                             limit=1)

                    if not public_holiday:
                        public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date),
                                                                                  ('line_id.company_id', '=', False)],
                                                                                 order='id desc', limit=1)
                    if not public_holiday and early_ot_responses != late_ot_responses and dayofweek != 6:
                        ot_hours += int(lot_diff) + 0.5 if round(lot_diff % 1, 2) >= 0.5 else int(lot_diff)
                if public_holiday and ot_hours == 0:
                    ot_hours += round(att.ot_hour,2)
                #if (self.struct_id and self.struct_id.shift == False and ot_hours > 8 and self.employee_id.resource_calendar_id.one_day_off == True) or (self.struct_id and self.struct_id.shift == False and ot_hours > 8 and self.employee_id.resource_calendar_id.holiday == True):
                #    ot_hours = 8
        return ot_hours
    
    def _check_resign_or_join_date_payslipmonth(self):
        end_date = self.date_to
        beg_date = self.date_from
        self.employee_id.id
        get_holiday = False
        calendar = self.employee_id.resource_calendar_id
        tz = timezone(calendar.tz)
        number_of_day = 0        
        
        
        if self.employee_id.joining_date and (datetime.strptime(str(self.employee_id.joining_date), '%Y-%m-%d').strftime("%Y-%m") == datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime("%Y-%m")):
            get_holiday = True  
        elif self.employee_id.resign_date and (datetime.strptime(str(self.employee_id.resign_date), '%Y-%m-%d').strftime("%Y-%m") == datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime("%Y-%m")): 
            get_holiday = True 
            
        if get_holiday == True and self.employee_id.resource_calendar_id.no_holidays == False:
            while beg_date <= end_date:
                dayofweek = beg_date.weekday()                
                work_hours = self._get_work_hours(beg_date, calendar, dayofweek)
                date_start = tz.localize((fields.Datetime.to_datetime(beg_date)).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
                date_stop = tz.localize((fields.Datetime.to_datetime(beg_date + timedelta(days=1))).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
                public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date),
                                                                      ('line_id.company_id', '=', self.employee_id.company_id.id)], order='id desc', limit=1)
                if (public_holiday and public_holiday.type == 'holiday') or (not public_holiday and dayofweek == 6):
#                     attendances = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
#                                                             ('check_in', '>=', date_start),
#                                                             ('check_in', '<', date_stop),('is_absent','=',False),('missed','=',False),('leave','=',False),
#                                                             ('state', 'in', ('approve', 'verify'))], order='check_in asc')
#                     if not attendances:
                    number_of_day += 1
                        
                beg_date = beg_date + timedelta(days=1)                
        return number_of_day
    def _get_unpaid_count(self):
        #leaves = self.env['summary.request'].search([('holiday_status_id','=',4),('employee_id','=',self.employee_id.id),('start_date','>=',self.date_from),('end_date','<=',self.date_to),('state','=','approve')])
        #from_date = datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime("%Y-%m")
        self.env.cr.execute("""select id from summary_request
        where holiday_status_id = 4 and state='approve' and employee_id=%s 
        and ((start_date>= %s and start_date <= %s) or (end_date>= %s and end_date <= %s))""",(self.employee_id.id,self.date_from,self.date_to,self.date_from,self.date_to,))
        #and to_char(start_date,'YYYY-MM') =%s and to_char(end_date,'YYYY-MM') =%s""",(self.employee_id.id,datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime("%Y-%m"),datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime("%Y-%m"),))
        result = self.env.cr.dictfetchall()
        
        if result:
            leaves = []
            total_day = 0 
            sunday_count = 0
            leave_day = 0            
            for leave in result:
                list_date = []
                print("leave>>>>",leave['id'])
                leaves.append(leave['id'])
                leave_id = self.env['summary.request'].browse([leave['id']])
                for line in self.env['summary.request.line'].search([('request_id','=',leave['id']),('date','>=',self.date_from),('date','<=',self.date_to)]):
                    if line.request_id.duration > 1:
                        list_date.append(line.date)
                    if line.full:
                        total_day += 1
                    elif line.first:
                        total_day += 0.5
                    elif line.second:
                        total_day += 0.5
                
                if len(list_date) > 0:
                    start_date = min(list_date)
                    end_date = max(list_date)
                    if start_date != end_date:
                        sunday_count += self.env['summary.request']._get_sunday_list(self.employee_id,start_date,end_date)
                 
            
            return sunday_count + total_day
        return 0
    def _get_worked_day_lines(self):
        res = super(HrPayslip, self)._get_worked_day_lines()
        for unpaid_line in res:
            if unpaid_line['work_entry_type_id'] == 5:
                unpaid_day = self._get_unpaid_count()
                print("unpaid_line>>>",unpaid_line)
                print("unpaid_line>>>",unpaid_line['work_entry_type_id'])
                print("unpaid_line>>>",unpaid_line['number_of_days'])
                print("before unpaid_day>>>>>>>>>>>>>>",unpaid_day)
                unpaid_line['number_of_days'] = unpaid_day
                if unpaid_day > float(unpaid_line['number_of_days']):
                    unpaid_day = unpaid_day - float(unpaid_line['number_of_days'])
                if unpaid_day > 0:
                    print("before sunday_unpaid>>>>>>>>>>>>>>",self.sunday_unpaid)
                    print("unpaid_day>>>>>>>>>>>>>>",unpaid_day)
                    self.sunday_unpaid = unpaid_day
                    
        #duty_structs = self.env['hr.payroll.structure'].search([('name', 'in', ('ST05', 'ST06', 'ST07'))])
        duty_structs = self.env['hr.payroll.structure'].search([('shift', '=', True)]) 
        meal_structs = self.env['hr.payroll.structure'].search([('meal_ot', '=', True)])       
        attendance_type = self.struct_id.type_id.default_work_entry_type_id
        calendar = self.employee_id.resource_calendar_id
        tz = timezone(calendar.tz)
        end_date = self.date_to
        beg_date = self.date_from
        delta = end_date - beg_date
        calendar_days = delta.days + 1
        number_of_days = number_of_hours = number_of_overtime_days = number_of_ot_hours = number_of_overtimegz_days= number_of_ot_gz_hours = 0
        no_attendance = one_day_off = no_holidays = False
        ot_gz = meal_ot = False
        
        res = [wdl for wdl in res if wdl['work_entry_type_id'] != attendance_type.id]
        test_ids = []
        while beg_date <= end_date:
            dayofweek = beg_date.weekday()
            print("beg_date>>",beg_date)
            work_hours = self._get_work_hours(beg_date, calendar, dayofweek)
            date_start = tz.localize((fields.Datetime.to_datetime(beg_date)).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
            date_stop = tz.localize((fields.Datetime.to_datetime(beg_date + timedelta(days=1))).replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)

            attendances = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                            ('check_in', '>=', date_start),
                                                            ('check_in', '<', date_stop),('is_absent','=',False),('missed','=',False),('leave','=',False),
                                                            ('state', 'in', ('approve', 'verify'))], order='check_in asc')

            employee_company = self.employee_id.company_id and self.employee_id.company_id.id or False
            
            calendar = self.employee_id.contract_id and self.employee_id.contract_id.resource_calendar_id or self.employee_id.resource_calendar_id
            domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', calendar.id), ('dayofweek', '=', str(dayofweek))]
            if calendar.two_weeks_calendar:
                week_type = int(math.floor((beg_date.toordinal() - 1) / 7) % 2)
                domain += [('week_type', '=', str(week_type))]

            working_hours = self.env['resource.calendar.attendance'].search(domain)
            public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date),
                                                                      ('line_id.company_id', '=', employee_company)], order='id desc', limit=1)
            
            
            if not public_holiday:
                public_holiday = self.env['public.holidays.line'].search([('date', '=', beg_date),
                                                                          ('line_id.company_id', '=', False)], order='id desc', limit=1)
            
            if public_holiday:
                if self.employee_id.resource_calendar_id.holiday == True or self.employee_id.resource_calendar_id.no_holidays == True or self.employee_id.resource_calendar_id.one_day_off == True:
                    ot_gz = True
#             else:
#                 if self.employee_id.resource_calendar_id.one_day_off == True and self.struct_id in duty_structs and dayofweek == 6:
#                     dayofweek = 1
                    
                    
            ot_duration = ot_hours = 0
            ot_responses = self.env['ot.request.line'].search([('employee_id', '=', self.employee_id.id),
                                                               ('start_date', '>=', date_start),
                                                               ('end_date', '<=', date_stop),
                                                               ('state', '=', 'accept')],
                                                              order='start_date asc')
            for ot_response in ot_responses:
                ot_duration += int(ot_response.duration) + 0.5 if round(ot_response.duration % 1, 2) >= 0.5 else int(ot_response.duration)
            if attendances:
                print(beg_date)
                no_worked_day = False
                for attend in attendances:
                    if attend.no_worked_day == True:
                        no_worked_day = attend.no_worked_day
                    
                
                if (public_holiday and public_holiday.type == 'holiday' and no_worked_day == False) or (not public_holiday and dayofweek == 6 and no_worked_day == False):
                    worked_hours = sum([round(att.worked_hours, 2) for att in attendances])
                    if len(self.employee_id.resource_calendar_id.attendance_ids) > 8:
                        worked_hours = 0
                        from_date = to_date = beg_date
                        for att in attendances:
                            print(att.check_in)
                            if att.check_in:
                                t_from_date = att.check_in + timedelta(hours=+6,minutes=+30)
                                from_date = t_from_date.date()
                            if att.check_out:
                                t_to_date = att.check_out + timedelta(hours=+6,minutes=+30)
                                to_date = t_to_date.date()
#                             print(from_date)
#                             print(from_date.date())
                            if att.id == 56383:
                                print("march 30")
                            if from_date == beg_date and to_date == beg_date:
                                worked_hours += round(att.worked_hours, 2)
                                test_ids.append(att.id)
                            
                            
                    #test_ids += attendances.ids
#                     if self.struct_id in duty_structs and ot_gz == False:
#                         number_of_overtime_days += 1 if worked_hours > 8 else 0.5
#                         if 8 < worked_hours < 16:
#                             ot_hours = 12
#                         elif worked_hours < 6:
#                             ot_hours = 6
#                         else:
#                             ot_hours = int(worked_hours) + 0.5 if round(worked_hours % 1, 2) >= 0.5 else int(worked_hours)
#                         number_of_ot_hours += ot_hours
                    if (self.employee_id.cooker == True and self.employee_id.resource_calendar_id.no_holidays == True) or (public_holiday and public_holiday.type == 'holiday' and self.employee_id.cooker == True and self.employee_id.resource_calendar_id.one_day_off == True):
                        number_of_ot_gz_hours += 4
                        
                    elif self.employee_id.resource_calendar_id.no_holidays == True or (public_holiday and public_holiday.type == 'holiday' and self.employee_id.resource_calendar_id.one_day_off == True and self.struct_id.shift == True):
                        number_of_overtimegz_days += 1 if worked_hours > 6 else 0.5
                        if self.employee_id.resource_calendar_id.hours_per_day > 10:
                            ot_hours = 12
                        elif self.employee_id.resource_calendar_id.hours_per_day >= 8:
                            ot_hours = 8
                        else:
                            ot_hours = 6#int(worked_hours) + 0.5 if round(worked_hours % 1, 2) >= 0.5 else int(worked_hours)
                        number_of_ot_gz_hours += ot_hours#worked_hours if worked_hours < ot_hours else ot_hours
                    
                    elif (not public_holiday and dayofweek == 6 and self.employee_id.resource_calendar_id.one_day_off == True): #or (not public_holiday and dayofweek == 6 and self.employee_id.resource_calendar_id.holiday == True):
                        ot_hours = self._get_ot_hours(attendances, ot_responses)
                        if (public_holiday and public_holiday.type == 'holiday') or (not public_holiday and dayofweek == 6): #check public holiday
                            if ot_hours != 0:
                                ot_hours =ot_duration if ot_duration < ot_hours else ot_hours
                            else:
                                ot_hours = ot_duration if ot_duration < worked_hours else worked_hours
                            
                            number_of_overtimegz_days += 1 if worked_hours > 6 else 0.5
                        number_of_ot_gz_hours += ot_hours 
                    elif (public_holiday and public_holiday.type == 'holiday' and self.employee_id.resource_calendar_id.one_day_off == True and self.struct_id.shift == False): #or (public_holiday and public_holiday.type == 'holiday'and self.employee_id.resource_calendar_id.holiday == True and self.struct_id.shift == False):
                        ot_hours = self._get_ot_hours(attendances, ot_responses)                        
#                         if ot_hours != 0:
#                             ot_hours =ot_duration if ot_duration < ot_hours else ot_hours
                        if ot_duration !=0:
                            ot_hours = ot_duration if ot_duration < worked_hours else worked_hours
                        else:
                            ot_hours = 8 if 8 < worked_hours else worked_hours
                        
                        number_of_overtimegz_days += 1 if worked_hours > 6 else 0.5
                        number_of_ot_gz_hours += ot_hours                            
                        #number_of_ot_gz_hours += worked_hours
                    # elif self.employee_id.resource_calendar_id.one_day_off == True or self.employee_id.resource_calendar_id.no_holidays == True:
                    #     ot_hours = self._get_ot_hours(attendances, ot_responses)
                    #     number_of_overtimegz_days += 1 if worked_hours > 6 else 0.5
                    #     number_of_ot_gz_hours += ot_duration if ot_duration < ot_hours else ot_hours
                    elif ot_responses:
                        ot_hours = self._get_ot_hours(attendances, ot_responses)
                        if (public_holiday and public_holiday.type == 'holiday') or (not public_holiday and dayofweek == 6): #check public holiday
                            #ot_hours = ot_duration if ot_duration < worked_hours else worked_hours
                            if ot_hours != 0:
                                ot_hours =ot_duration if ot_duration < ot_hours else ot_hours
                            elif ot_duration !=0:
                                ot_hours = ot_duration if ot_duration < worked_hours else worked_hours
                            number_of_overtimegz_days += 1 if worked_hours > 6 else 0.5
                            number_of_ot_gz_hours += ot_hours                        
                        else:
                            number_of_overtime_days += 1 if worked_hours > 6 else 0.5
                            number_of_ot_hours += ot_duration if ot_duration < ot_hours else ot_hours
                else:
                    if work_hours:
                        if len(work_hours) == len(attendances):
                            number_of_days += 1
                            number_of_hours += sum([int(att.worked_hours) for att in attendances])
                        elif len(work_hours) == 2 and len(attendances) == 1:
                            number_of_days += 0.5
                            number_of_hours += int(attendances.worked_hours)
                        # if self.struct_id in duty_structs:
                        #     print("ST in STs")
                        #     for att in attendances:
                        #         ot_hours += int(att.ot_hour) + 0.5 if round(att.ot_hour % 1, 2) >= 0.5 else int( att.ot_hour)
                        #         ot_hours += int(att.early_ot_hour) + 0.5 if round(att.early_ot_hour % 1, 2) >= 0.5 else int(att.early_ot_hour)
                        #     number_of_ot_hours += ot_hours
                        if ot_responses:
                            ot_hours = self._get_ot_hours(attendances, ot_responses)
                            print("ot hours: ", ot_hours)
                            number_of_ot_hours += ot_duration if ot_duration < ot_hours else ot_hours
                    else:
                        average_hours_per_day = round(calendar.hours_per_day, 1)
                        worked_hours = sum([int(att.worked_hours) for att in attendances])
                        number_of_hours += worked_hours
                        if (average_hours_per_day * 0.75) > worked_hours:
                            number_of_days += 0.5
                        else:
                            number_of_days += 1

                        if worked_hours > average_hours_per_day:
                            ot_hours = worked_hours - average_hours_per_day
                            ot_hours = int(ot_hours) + 0.5 if round(ot_hours % 1, 2) >= 0.5 else int(ot_hours)
                        if self.struct_id in duty_structs and work_hours:
                            number_of_ot_hours += ot_hours
                        elif ot_responses:
                            number_of_ot_hours += ot_duration if ot_duration < ot_hours else ot_hours
            beg_date = beg_date + timedelta(days=1)
        
        #added paid leave to attendance number of days
        contract = self.employee_id.contract_id
        if contract.resource_calendar_id:
            paid_amount = self._get_contract_wage()
            unpaid_work_entry_types = self.struct_id.unpaid_work_entry_type_ids.ids

            work_hours = contract._get_work_hours(self.date_from, self.date_to)
            total_hours = sum(work_hours.values()) or 1
            work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
            biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
            add_days_rounding = 0
            for work_entry_type_id, hours in work_hours_ordered:
                work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
                is_paid = work_entry_type_id not in unpaid_work_entry_types
                calendar = contract.resource_calendar_id
                days = round(hours / calendar.hours_per_day, 5) if calendar.hours_per_day else 0
                if work_entry_type_id == biggest_work:
                    days += add_days_rounding
                day_rounded = self._round_days(work_entry_type, days)
                add_days_rounding += (days - day_rounded)
                number_of_days += day_rounded
                number_of_hours += hours
        
        get_number_sunday = self._check_resign_or_join_date_payslipmonth()
        
        number_of_days += get_number_sunday 
        if self.employee_id.joining_date and (datetime.strptime(str(self.employee_id.joining_date), '%Y-%m-%d').strftime("%Y-%m") == datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime("%Y-%m")):
            number_of_days = self.half_month_day  
            print("joining date>>>>",self.employee_id.joining_date)
        elif self.employee_id.resign_date and (datetime.strptime(str(self.employee_id.resign_date), '%Y-%m-%d').strftime("%Y-%m") == datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime("%Y-%m")): 
            number_of_days = self.half_month_day 
            
        if number_of_hours > 0 or number_of_days > 0:
            attendance_line = {'sequence': attendance_type.sequence,
                               'work_entry_type_id': attendance_type.id,
                               'number_of_days': number_of_days,
                               'number_of_hours': number_of_hours,
                               'amount': number_of_ot_hours * (((self.contract_id.wage * 12) / 52) / 6),
                               }
            res.append(attendance_line)        
        
        
        if self.struct_id in meal_structs:       
            meal_ot = True
            number_of_ot_hours += number_of_ot_gz_hours
            number_of_overtime_days += number_of_overtimegz_days
            number_of_ot_gz_hours = 0
            number_of_overtimegz_days = 0
            
        if number_of_ot_hours > 0:
            work_entry_type = self.env.ref('hr_payroll_ext.work_entry_type_overtime')
            paid_amount = ((self.contract_id.wage * 12 *2) / (52*48)) #(((self.contract_id.wage * 12) / 52) / 48) * 2
            if meal_ot == True:
                paid_amount = 0
            print("number_of_ot_hours>>>",(((self.contract_id.wage * 12) / 52) / 48) * 2)
            overtime_line = {'sequence': work_entry_type.sequence,
                             'work_entry_type_id': work_entry_type.id,
                             'number_of_days': number_of_overtime_days,
                             'number_of_hours': number_of_ot_hours,
                             'amount': number_of_ot_hours * paid_amount,
                             }
            res.append(overtime_line)
        print("OT GZ>>>", test_ids)
        if number_of_ot_gz_hours > 0:
            work_entry_type = self.env.ref('hr_payroll_ext.work_entry_type_overtimegz')
#             if len(self.employee_id.resource_calendar_id.attendance_ids) > 8:
#                 #paid_amount = ((self.contract_id.wage / calendar_days)/8)
#                 print("number_of_ot_gz_hours>>>",self.contract_id.wage,calendar_days)
#                 print("number_of_ot_gz_hours by day>>>",(((self.contract_id.wage / calendar_days) / 8) * 2))
#                 print("number_of_ot_gz_hours by day round>>>",round((((self.contract_id.wage / calendar_days) / 8) * 2),2))
#                 paid_amount = (((self.contract_id.wage / calendar_days) / 8) * 2) * number_of_ot_gz_hours 
#             else:
                #paid_amount = (((self.contract_id.wage * 12) / 52) / 48) * 2
            hours = int(number_of_ot_gz_hours)
            minutes = (number_of_ot_gz_hours*60) % 60
            print("minutes>>>>",minutes,minutes/100,hours +(minutes/100) )
            print("math.floor(number_of_ot_gz_hours)>>",math.floor(number_of_ot_gz_hours))
            #print("min>>>>",int((number_of_ot_gz_hours%(math.floor(number_of_ot_gz_hours)))*60))
            print("hours>>>>",hours )
            if minutes >= 30:
                number_of_ot_gz_hours = hours +(0.5)
            elif hours >=1:
                print("hours change>>>>",hours )
                number_of_ot_gz_hours = hours              
            else:
                number_of_ot_gz_hours = 0   
            paid_amount = ((self.contract_id.wage * 12 *2) / (52*48)) * number_of_ot_gz_hours #((((self.contract_id.wage * 12) / 52) / 48) * 2) * number_of_ot_gz_hours
            
            overtime_line = {'sequence': work_entry_type.sequence,
                             'work_entry_type_id': work_entry_type.id,
                             'number_of_days': number_of_overtimegz_days,
                             'number_of_hours': number_of_ot_gz_hours,
                             'amount': paid_amount,
                             }
            res.append(overtime_line)
        else:
            work_entry_type = self.env.ref('hr_payroll_ext.work_entry_type_overtimegz')
            overtime_line = {'sequence': work_entry_type.sequence,
                             'work_entry_type_id': work_entry_type.id,
                             'number_of_days': 0,
                             'number_of_hours': 0,
                             'amount': 0,
                             }
            res.append(overtime_line)
            #print(test_ids)
        absent_line = self._get_absent_day_lines()
        if absent_line:
            res.append(absent_line)

        fp_missed_line = self._get_fp_missed_lines()
        if fp_missed_line:
            res.append(fp_missed_line)
        
        early_late_line = self._get_late_early_day_lines()
        if early_late_line:
            res.append(early_late_line)
        return res

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        fiscal_year = self.env['account.fiscal.year'].search([('date_from', '<=', self.date_to),
                                                              ('date_to', '>=', self.date_to)])
        if not fiscal_year:
            action = self.env.ref('account.actions_account_fiscal_year')
            raise RedirectWarning(_('You should configure a Fiscal Year first.'), action.id, _('Fiscal Years'))

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        last_month = date_from + timedelta(days=-1)
        last_month_slip = self.env['hr.payslip'].search([('date_to','=',last_month),('employee_id','=',employee.id),('state','=','done')],limit=1)

        if not last_month_slip:
            if self.employee_id.joining_date.month != date_from.month and self.employee_id.joining_date.year != date_from.year:
                raise ValidationError(_('%s Payroll not allowed skip month. Payslip month must be run incremental')% (employee.name))

        print("employee : ", employee.id)
        self.company_id = employee.company_id
        if not self.contract_id or self.employee_id != self.contract_id.employee_id:  # Add a default contract if not already defined
            contracts = employee._get_contracts(date_from, date_to)
            print("no contracts")
            if not contracts:
                self.contract_id = False
                self.struct_id = False
                return
            self.contract_id = contracts[0]
            self.struct_id = contracts[0].struct_id or contracts[0].structure_type_id.default_struct_id

        payslip_name = self.struct_id.payslip_name or _('Salary Slip')
        self.name = '%s - %s - %s' % (
        payslip_name, self.employee_id.name or '', format_date(self.env, self.date_from, date_format="MMMM y"))

        if date_to > date_utils.end_of(fields.Date.today(), 'month'):
            self.warning_message = _(
                "This payslip can be erroneous! Work entries may not be generated for the period from %s to %s." %
                (date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1), date_to))
        else:
            self.warning_message = False

        self.worked_days_line_ids = self._get_new_worked_days_lines()
        self.input_line_ids = self._get_new_input_lines()

    # def action_payslip_done(self):
    #     for line in self.input_line_ids:
    #         if line.loan_line_ids:
    #             for loan_line in line.loan_line_ids:
    #                 loan_line.write({'state': 'paid'})
    #                 loan_line.write({'paid': True})
    #                 loan_line.loan_id._compute_loan_amount()
    #         if line.insurance_line_ids:
    #             for line in line.insurance_line_ids:
    #                 line.write({'state': 'paid'})
    #                 line.write({'paid': True})
    #                 line.insurance_id._compute_insurance_amount()

    #     res = super(HrPayslip, self).action_payslip_done()
    #     for rec in self:
    #         one_signal_values = {'employee_id': rec.employee_id.id,
    #                                     'contents': _('%s Payslip for %s-%s') % (rec.employee_id.name, rec.date_from,rec.date_to),
    #                                     'headings': _('WB B2B : Payslip CREATED')}
    #         self.env['one.signal.notification.message'].create(one_signal_values)
        
    #     for slip in self:
    #         move = slip.move_id
    #         line_ids = move.line_ids
    #         if move and line_ids and move.state == 'draft':
    #             analytic_tag_ids = []
    #             contract = slip.contract_id
    #             analytic_tag_ids += contract.analytic_tag_id and [contract.analytic_tag_id.id] or []
    #             analytic_tag_ids += contract.job_grade_id and contract.job_grade_id.analytic_tag_id and [contract.job_grade_id.analytic_tag_id.id] or []
    #             for line in line_ids:
    #                 line.write({'analytic_tag_ids': [(6, 0, analytic_tag_ids)]})
    #     return res

    def action_payslip_done(self):
        for line in self.input_line_ids:
            if line.loan_line_ids:
                for loan_line in line.loan_line_ids:
                    loan_line.write({'state': 'paid'})
                    loan_line.write({'paid': True})
                    loan_line.loan_id._compute_loan_amount()
            if line.insurance_line_ids:
                for line in line.insurance_line_ids:
                    line.write({'state': 'paid'})
                    line.write({'paid': True})
                    line.insurance_id._compute_insurance_amount()

        res = super(HrPayslip, self).action_payslip_done()
        precision = self.env['decimal.precision'].precision_get('Payroll')

        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)
        
        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            payslips_to_post |= run.slip_ids
            # if run._are_payslips_ready():
            #     payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))
        
        # Map all payslips by structure journal and pay slips month.
        # {'journal_id': {'month': [slip_ids]}}
        slip_mapped_data = {slip.struct_id.journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip in payslips_to_post}
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip
        
        for journal_id in slip_mapped_data:
            for slip_date in slip_mapped_data[journal_id]: 
                # line_ids = []
                # debit_sum = 0.0
                # credit_sum = 0.0
                date = slip_date
                move_dict = {
                    'narration': '',
                    'ref': date.strftime('%B %Y'),
                    'journal_id': journal_id,
                    'date': date,
                }
                for slip in slip_mapped_data[journal_id][slip_date]:
                    print("slip>>>>",slip.id,slip.employee_id.id)
                    move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                    move_dict['narration'] += '\n'
                    move_dict['partner_id'] = slip.employee_id.address_home_id.id
                    line_ids = []
                    debit_sum = 0.0
                    credit_sum = 0.0

                    gross_line = slip.line_ids.filtered(lambda line: line.code == 'GROSS')
                    gross_amount = gross_line.total

                    analytic_tag_list = []
                    analytic_tag_list.append(slip.employee_id.department_id.analytic_tag_id.id)
                    domain = [('company_id', '=', slip.company_id.id)] #, ('branch_id', '=', slip.employee_id.branch_id.id)]
                    if slip.struct_id.is_management:
                        domain += [('name', '=', 'Management')]
                    elif slip.struct_id.is_manager:
                        domain += [('name', '=', 'Manager')]
                    elif slip.struct_id.is_staff:
                        domain += [('name', '=', 'Staff')]
                    analytic_tag_obj = self.env['account.analytic.tag'].search(domain, limit=1)
                    analytic_tag_list.append(analytic_tag_obj.id)
                    print("####", analytic_tag_list)
                    for line in slip.line_ids.filtered(lambda line: line.category_id):
                        # amount = -line.total if slip.credit_note else line.total
                        amount = -gross_amount if slip.credit_note else gross_amount
                        if line.code == 'NET': 
                            for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                if tmp_line.salary_rule_id.not_computed_in_net:
                                    if amount > 0:
                                        amount -= abs(tmp_line.total)
                                    elif amount < 0:
                                        amount += abs(tmp_line.total)
                        if float_is_zero(amount, precision_digits=precision):
                            continue
                        debit_account_id = line.salary_rule_id.account_debit.id
                        credit_account_id = line.salary_rule_id.account_credit.id

                        if debit_account_id: 
                            debit = amount if amount > 0.0 else 0.0
                            credit = -amount if amount < 0.0 else 0.0

                            existing_debit_lines = (
                                line_id for line_id in line_ids if
                                line_id['name'] == line.name
                                and line_id['account_id'] == debit_account_id
                                and line_id['analytic_account_id'] == slip.employee_id.branch_id.analytic_account_id.id
                                and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
                            debit_line = next(existing_debit_lines, False)

                            if not debit_line:
                                debit_line = {
                                    'name': line.name,
                                    'partner_id': slip.employee_id.address_home_id.id,
                                    'account_id': debit_account_id,
                                    'journal_id': slip.struct_id.journal_id.id,
                                    'date': date,
                                    'debit': debit,
                                    'credit': credit,
                                    'analytic_account_id': slip.employee_id.branch_id.analytic_account_id.id,
                                    'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                }
                                line_ids.append(debit_line)
                            else:
                                debit_line['debit'] += debit
                                debit_line['credit'] += credit
                        
                        if credit_account_id:
                            debit = -amount if amount < 0.0 else 0.0
                            credit = amount if amount > 0.0 else 0.0
                            existing_credit_line = (
                                line_id for line_id in line_ids if
                                line_id['name'] == line.name
                                and line_id['account_id'] == credit_account_id
                                and line_id['analytic_account_id'] == slip.employee_id.branch_id.analytic_account_id.id
                                and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0))
                            )
                            credit_line = next(existing_credit_line, False)

                            if not credit_line:
                                credit_line = {
                                    'name': line.name,
                                    'partner_id': slip.employee_id.address_home_id.id,
                                    'account_id': credit_account_id,
                                    'journal_id': slip.struct_id.journal_id.id,
                                    'date': date,
                                    'debit': debit,
                                    'credit': credit,
                                    'analytic_account_id': slip.employee_id.branch_id.analytic_account_id.id,
                                    'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                }
                                line_ids.append(credit_line)
                            else:
                                credit_line['debit'] += debit
                                credit_line['credit'] += credit
                
                    for line_id in line_ids: 
                        debit_sum += line_id['debit']
                        credit_sum += line_id['credit']

                    # The code below is called if there is an error in the balance between credit and debit sum.
                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                        acc_id = slip.journal_id.default_credit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_credit = next(existing_adjustment_line, False)

                        if not adjust_credit:
                            adjust_credit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.journal_id.id,
                                'date': date,
                                'debit': 0.0,
                                'credit': debit_sum - credit_sum,
                            }
                            line_ids.append(adjust_credit)
                        else:
                            adjust_credit['credit'] = debit_sum - credit_sum

                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                        acc_id = slip.journal_id.default_debit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_debit = next(existing_adjustment_line, False)

                        if not adjust_debit:
                            adjust_debit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.journal_id.id,
                                'date': date,
                                'debit': credit_sum - debit_sum,
                                'credit': 0.0,
                            }
                            line_ids.append(adjust_debit)
                        else:
                            adjust_debit['debit'] = credit_sum - debit_sum

                    # Add accounting lines in the move
                    move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                    move = self.env['account.move'].create(move_dict)
                    slip.write({'move_id': move.id, 'date': date})
        print("_create_misc_accounting_entry>>>>")
        self._create_misc_accounting_entry()
        if self.misc_move_id and self.misc_move_id.line_ids:
            print("_create_misc_purchase_order>>>>")
            self._create_misc_purchase_order()
        print("_create_logistics_commission_accounting_entry>>>>")
        self._create_logistics_commission_accounting_entry()
        if self.logistics_move_id and self.logistics_move_id.line_ids:
            print("_create_logistics_purchase_order>>>>")
            self._create_logistics_purchase_order()
        
        for rec in self:
            one_signal_values = {'employee_id': rec.employee_id.id,
                                'contents': _('%s Payslip for %s-%s') % (rec.employee_id.name, rec.date_from,rec.date_to),
                                'headings': _('WB B2B : Payslip CREATED')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        
        return res
    
    def _create_misc_accounting_entry(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            payslips_to_post |= run.slip_ids
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.misc_move_id)
        
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.misc_journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no misc account journal defined on it.'))
        
        slip_mapped_data = {slip.struct_id.misc_journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip in payslips_to_post}
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.misc_journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip
        
        print("######")
        print(slip_mapped_data)
        for journal_id in slip_mapped_data:
            for slip_date in slip_mapped_data[journal_id]:
                date = slip_date
                move_dict = {
                    'narration': '',
                    'ref': date.strftime('%B %Y'),
                    'journal_id': journal_id,
                    'date': date,
                }
                for slip in slip_mapped_data[journal_id][slip_date]:
                    print("slip: ", slip)
                    print(slip.employee_id.name)
                    move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                    move_dict['narration'] += '\n'
                    move_dict['partner_id'] = slip.employee_id.address_home_id.id
                    line_ids = []
                    debit_sum = 0.0
                    credit_sum = 0.0

                    analytic_tag_list = []
                    analytic_tag_list.append(slip.employee_id.department_id.analytic_tag_id.id)
                    domain = [('company_id', '=', slip.company_id.id)]
                    if slip.struct_id.is_management:
                        domain += [('name', '=', 'Management')]
                    elif slip.struct_id.is_manager:
                        domain += [('name', '=', 'Manager')]
                    elif slip.struct_id.is_staff:
                        domain += [('name', '=', 'Staff')]
                    analytic_tag_obj = self.env['account.analytic.tag'].search(domain, limit=1)
                    analytic_tag_list.append(analytic_tag_obj.id)

                    for line in slip.line_ids.filtered(lambda line: line.category_id):
                        amount = -line.total if slip.credit_note else line.total
                        if line.code in ('SSB', 'ELOAN', 'TLOAN', 'ICT', 'INS', 'OT', 'OTDT', 'OTGZ', 'OTALW') and line.total != 0.0:
                            debit_account_id = None
                            credit_account_id = None
                            for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                if tmp_line.salary_rule_id.not_computed_in_net:
                                    if amount > 0:
                                        amount -= abs(tmp_line.total)
                                    elif amount < 0:
                                        amount += abs(tmp_line.total)
                            if float_is_zero(amount, precision_digits=precision):
                                continue
                            if line.code in ('ELOAN', 'TLOAN'):
                                loan = self.env['hr.loan.line'].sudo().search([('employee_id', '=', slip.employee_id.id),
                                                                              ('date', '>=', slip.date_from),
                                                                              ('date', '<=', slip.date_to),
                                                                              ('loan_id.state', '=', ('verify','approve'))], limit=1)
                                if loan:
                                    debit_account_id = loan.loan_id.treasury_account_id.id if loan.loan_id.treasury_account_id else False
                                    credit_account_id = loan.loan_id.emp_account_id.id if loan.loan_id.emp_account_id else False
                                    if not debit_account_id:
                                        raise UserError(_('Please define treasury account in loan.'))
                                    if not credit_account_id:
                                        raise UserError(_('Please define loan account in loan.'))
                            else:
                                debit_account_id = line.salary_rule_id.debit_account_misc.id
                                credit_account_id = line.salary_rule_id.credit_account_misc.id
                            print(amount)
                            print("debit acc : ", debit_account_id)
                            print("credit acc : ", credit_account_id)
                            if debit_account_id: 
                                debit = amount if amount > 0.0 else 0.0
                                credit = -amount if amount < 0.0 else 0.0

                                existing_debit_lines = (
                                    line_id for line_id in line_ids if
                                    line_id['name'] == line.name
                                    and line_id['account_id'] == debit_account_id
                                    and line_id['analytic_account_id'] == slip.employee_id.branch_id.analytic_account_id.id
                                    and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
                                debit_line = next(existing_debit_lines, False)

                                if not debit_line:
                                    debit_line = {
                                        'name': line.name,
                                        'partner_id': slip.employee_id.address_home_id.id,
                                        'account_id': debit_account_id,
                                        'journal_id': slip.struct_id.misc_journal_id.id,
                                        'date': date,
                                        'debit': debit,
                                        'credit': credit,
                                        'analytic_account_id': slip.employee_id.branch_id.analytic_account_id.id,
                                        'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                    }
                                    line_ids.append(debit_line)
                                else:
                                    debit_line['debit'] += debit
                                    debit_line['credit'] += credit
                        
                            if credit_account_id: 
                                debit = -amount if amount < 0.0 else 0.0
                                credit = amount if amount > 0.0 else 0.0
                                existing_credit_line = (
                                    line_id for line_id in line_ids if
                                    line_id['name'] == line.name
                                    and line_id['account_id'] == credit_account_id
                                    and line_id['analytic_account_id'] == slip.employee_id.branch_id.analytic_account_id.id
                                    and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0))
                                )
                                credit_line = next(existing_credit_line, False)

                                if not credit_line:
                                    credit_line = {
                                        'name': line.name,
                                        'partner_id': slip.employee_id.address_home_id.id,
                                        'account_id': credit_account_id,
                                        'journal_id': slip.struct_id.misc_journal_id.id,
                                        'date': date,
                                        'debit': debit,
                                        'credit': credit,
                                        'analytic_account_id': slip.employee_id.branch_id.analytic_account_id.id,
                                        'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                    }
                                    line_ids.append(credit_line)
                                else:
                                    credit_line['debit'] += debit
                                    credit_line['credit'] += credit
                
                    for line_id in line_ids: 
                        debit_sum += line_id['debit']
                        credit_sum += line_id['credit']
                
                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                        acc_id = slip.misc_journal_id.default_credit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.misc_journal_id.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_credit = next(existing_adjustment_line, False)

                        if not adjust_credit:
                            adjust_credit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.misc_journal_id.id,
                                'date': date,
                                'debit': 0.0,
                                'credit': debit_sum - credit_sum,
                            }
                            line_ids.append(adjust_credit)
                        else:
                            adjust_credit['credit'] = debit_sum - credit_sum

                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                        acc_id = slip.misc_journal_id.default_debit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.misc_journal_id.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_debit = next(existing_adjustment_line, False)

                        if not adjust_debit:
                            adjust_debit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.misc_journal_id.id,
                                'date': date,
                                'debit': credit_sum - debit_sum,
                                'credit': 0.0,
                            }
                            line_ids.append(adjust_debit)
                        else:
                            adjust_debit['debit'] = credit_sum - debit_sum

                    move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                    move = self.env['account.move'].create(move_dict)
                    slip.write({'misc_move_id': move.id})
                    
    def _create_misc_purchase_order(self):
        for rec in self:
            if rec.misc_move_id:    
                po_values = {
                                'partner_id': rec.employee_id.address_home_id.id,
                                'company_id': rec.company_id.id,
                                'payslip_id': rec.id,                            
                            }
                purchase_order = self.env['purchase.order'].sudo().create(po_values)
                move_lines = rec.misc_move_id.line_ids.filtered(lambda line: line.debit > 0)
                for line in move_lines:
    #                 if 'loan' in line.name.lower():
    #                     if line.name.lower() == 'loan entitlement':
    #                         product_obj = self.env['product.product'].search([('is_loan', '=', True),
    #                                                                           ('company_id', '=', self.company_id.id),
    #                                                                           ('name', 'ilike', 'loan entitlement')], limit=1)
    #                     if line.name.lower() == 'training loan':
    #                         product_obj = self.env['product.product'].search([('is_loan', '=', True),
    #                                                                           ('company_id', '=', self.company_id.id),
    #                                                                           ('name', 'ilike', 'training loan')], limit=1)
    #                     if product_obj:
    #                         product_id = product_obj.id                        
    #                         loan_line = {
    #                                 'product_id': product_id,  
    #                                 'name': product_obj.display_name,    
    #                                 'product_qty': 1,    
    #                                 'product_uom': product_obj.uom_id.id,                             
    #                                 'price_unit': abs(line.debit-line.credit),
    #                                 'order_id': purchase_order.id,
    #                                 'date_planned': datetime.now(), 
    #                                 'account_analytic_id': line.analytic_account_id.id if line.analytic_account_id else None,
    #                                 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids if line.analytic_tag_ids else [])]                              
    #                             }
    #                         self.env['purchase.order.line'].create(loan_line)
                    if 'ssb' in line.name.lower():
                        if rec.struct_id.is_management == True:
                            product_obj = self.env['product.product'].search([('is_ssb', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', 'Management')], limit=1)
                        elif rec.struct_id.is_manager == True:
                            product_obj = self.env['product.product'].search([('is_ssb', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', 'Manager')], limit=1)
                        elif rec.struct_id.is_staff == True:
                            product_obj = self.env['product.product'].search([('is_ssb', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', 'Staff')], limit=1)
                        if product_obj:
                            product_id = product_obj.id
                            ssb_line = {
                                    'product_id': product_id,  
                                    'name': product_obj.display_name,
                                    'product_qty': 1,               
                                    'product_uom': product_obj.uom_id.id,                               
                                    'price_unit': abs(line.debit-line.credit),
                                    'order_id': purchase_order.id,    
                                    'date_planned': datetime.now(),
                                    'account_analytic_id': line.analytic_account_id.id if line.analytic_account_id else None,
                                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids if line.analytic_tag_ids else [])]                               
                                }
                            self.env['purchase.order.line'].sudo().create(ssb_line)
                    elif 'income tax' in line.name.lower():
                        if rec.struct_id.is_management == True:
                            product_obj = self.env['product.product'].search([('is_tax', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', 'Management')], limit=1)
                        elif rec.struct_id.is_manager == True:
                            product_obj = self.env['product.product'].search([('is_tax', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', 'Manager')], limit=1)
                        elif rec.struct_id.is_staff == True:
                            product_obj = self.env['product.product'].search([('is_tax', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', 'Staff')], limit=1)
                        if product_obj:
                            product_id = product_obj.id
                            tax_line = {
                                    'product_id': product_id,      
                                    'name': product_obj.display_name,  
                                    'product_qty': 1,        
                                    'product_uom': product_obj.uom_id.id,                            
                                    'price_unit': abs(line.debit-line.credit),
                                    'order_id': purchase_order.id,      
                                    'date_planned': datetime.now(),  
                                    'account_analytic_id': line.analytic_account_id.id if line.analytic_account_id else None,
                                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids if line.analytic_tag_ids else [])]                           
                                }
                            self.env['purchase.order.line'].sudo().create(tax_line)
                    elif 'ot' in line.name.lower():
                        if line.name.lower() == 'ot':
                            product_obj = self.env['product.product'].search([('is_ot', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', line.name.lower())], limit=1)
                        elif line.name.lower() == 'ot duty':
                            product_obj = self.env['product.product'].search([('is_ot', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', line.name.lower())], limit=1)
                        elif line.name.lower() == 'ot gz':
                            product_obj = self.env['product.product'].search([('is_ot', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', line.name.lower())], limit=1)
                        elif line.name.lower() == 'ot allowance':
                            product_obj = self.env['product.product'].search([('is_ot', '=', True),
                                                                            ('company_id', '=', rec.company_id.id),
                                                                            ('name', 'ilike', line.name.lower())], limit=1)
                        if product_obj:
                            product_id = product_obj.id                        
                            ot_line = {
                                    'product_id': product_id,  
                                    'name': product_obj.display_name,    
                                    'product_qty': 1,    
                                    'product_uom': product_obj.uom_id.id,                             
                                    'price_unit': abs(line.debit-line.credit),
                                    'order_id': purchase_order.id,
                                    'date_planned': datetime.now(), 
                                    'account_analytic_id': line.analytic_account_id.id if line.analytic_account_id else None,
                                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids if line.analytic_tag_ids else [])]                              
                                }
                            self.env['purchase.order.line'].sudo().create(ot_line)
    
    def _create_logistics_commission_accounting_entry(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            payslips_to_post |= run.slip_ids
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.logistics_move_id)
        
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        
        slip_mapped_data = {slip.struct_id.logistics_commission_journal.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip in payslips_to_post}
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.logistics_commission_journal.id][fields.Date().end_of(slip.date_to, 'month')] |= slip
        
        for journal_id in slip_mapped_data:
            for slip_date in slip_mapped_data[journal_id]:
                date = slip_date
                if journal_id:
                    move_dict = {
                        'narration': '',
                        'ref': date.strftime('%B %Y'),
                        'journal_id': journal_id,
                        'date': date,
                    }
                else:
                    move_dict = {
                        'narration': '',
                        'ref': date.strftime('%B %Y'),
                        # 'journal_id': journal_id,
                        'date': date,
                    }
                        
                for slip in slip_mapped_data[journal_id][slip_date]:
                    move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                    move_dict['narration'] += '\n'
                    move_dict['partner_id'] = slip.employee_id.address_home_id.id
                    line_ids = []
                    debit_sum = 0.0
                    credit_sum = 0.0

                    analytic_tag_list = []
                    analytic_tag_list.append(slip.employee_id.department_id.analytic_tag_id.id)
                    domain = [('company_id', '=', slip.company_id.id)]
                    if slip.struct_id.is_management:
                        domain += [('name', '=', 'Management')]
                    elif slip.struct_id.is_manager:
                        domain += [('name', '=', 'Manager')]
                    elif slip.struct_id.is_staff:
                        domain += [('name', '=', 'Staff')]
                    analytic_tag_obj = self.env['account.analytic.tag'].search(domain, limit=1)
                    analytic_tag_list.append(analytic_tag_obj.id)

                    for line in slip.line_ids.filtered(lambda line: line.category_id):
                        amount = -line.total if slip.credit_note else line.total
                        if line.code == 'A06' and line.total != 0.0:
                            for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                if tmp_line.salary_rule_id.not_computed_in_net:
                                    if amount > 0:
                                        amount -= abs(tmp_line.total)
                                    elif amount < 0:
                                        amount += abs(tmp_line.total)
                            if float_is_zero(amount, precision_digits=precision):
                                continue
                            debit_account_id = line.salary_rule_id.commission_debit_account.id
                            credit_account_id = line.salary_rule_id.commission_credit_account.id
                            
                            if debit_account_id: 
                                debit = amount if amount > 0.0 else 0.0
                                credit = -amount if amount < 0.0 else 0.0

                                existing_debit_lines = (
                                    line_id for line_id in line_ids if
                                    line_id['name'] == line.name
                                    and line_id['account_id'] == debit_account_id
                                    and line_id['analytic_account_id'] == slip.employee_id.branch_id.analytic_account_id.id
                                    and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
                                debit_line = next(existing_debit_lines, False)

                                if not debit_line:
                                    debit_line = {
                                        'name': line.name,
                                        'partner_id': slip.employee_id.address_home_id.id,
                                        'account_id': debit_account_id,
                                        'journal_id': slip.struct_id.logistics_commission_journal.id,
                                        'date': date,
                                        'debit': debit,
                                        'credit': credit,
                                        'analytic_account_id': slip.employee_id.branch_id.analytic_account_id.id,
                                        'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                    }
                                    line_ids.append(debit_line)
                                else:
                                    debit_line['debit'] += debit
                                    debit_line['credit'] += credit
                        
                            if credit_account_id: 
                                debit = -amount if amount < 0.0 else 0.0
                                credit = amount if amount > 0.0 else 0.0
                                existing_credit_line = (
                                    line_id for line_id in line_ids if
                                    line_id['name'] == line.name
                                    and line_id['account_id'] == credit_account_id
                                    and line_id['analytic_account_id'] == slip.employee_id.branch_id.analytic_account_id.id
                                    and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0))
                                )
                                credit_line = next(existing_credit_line, False)

                                if not credit_line:
                                    credit_line = {
                                        'name': line.name,
                                        'partner_id': slip.employee_id.address_home_id.id,
                                        'account_id': credit_account_id,
                                        'journal_id': slip.struct_id.logistics_commission_journal.id,
                                        'date': date,
                                        'debit': debit,
                                        'credit': credit,
                                        'analytic_account_id': slip.employee_id.branch_id.analytic_account_id.id,
                                        'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                    }
                                    line_ids.append(credit_line)
                                else:
                                    credit_line['debit'] += debit
                                    credit_line['credit'] += credit
                
                    for line_id in line_ids: 
                        debit_sum += line_id['debit']
                        credit_sum += line_id['credit']
                
                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                        acc_id = slip.logistics_commission_journal.default_credit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.logistics_commission_journal.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_credit = next(existing_adjustment_line, False)

                        if not adjust_credit:
                            adjust_credit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.logistics_commission_journal.id,
                                'date': date,
                                'debit': 0.0,
                                'credit': debit_sum - credit_sum,
                            }
                            line_ids.append(adjust_credit)
                        else:
                            adjust_credit['credit'] = debit_sum - credit_sum

                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                        acc_id = slip.logistics_commission_journal.default_debit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.logistics_commission_journal.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_debit = next(existing_adjustment_line, False)

                        if not adjust_debit:
                            adjust_debit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.logistics_commission_journal.id,
                                'date': date,
                                'debit': credit_sum - debit_sum,
                                'credit': 0.0,
                            }
                            line_ids.append(adjust_debit)
                        else:
                            adjust_debit['debit'] = credit_sum - debit_sum

                    move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                    move = self.env['account.move'].create(move_dict)
                    slip.write({'logistics_move_id': move.id})

    def _create_logistics_purchase_order(self):
        for rec in self:
            if rec.logistics_move_id:  
                print("self.employee_id>>>>",rec.employee_id)  
                po_values = {
                                'partner_id': rec.employee_id.address_home_id.id,
                                'company_id': rec.company_id.id,
                                'payslip_id': rec.id,                            
                            }
                purchase_order = self.env['purchase.order'].sudo().create(po_values)
                move_lines = rec.logistics_move_id.line_ids.filtered(lambda line: line.debit > 0)
                for line in move_lines:
                    if 'commission' in line.name.lower():
                        product_obj = self.env['product.product'].search([('is_commision', '=', True),
                                                                          ('company_id', '=', self.company_id.id)], limit=1)
                        if product_obj:
                            product_id = product_obj.id                        
                            commission_line = {
                                    'product_id': product_id,  
                                    'name': product_obj.display_name,    
                                    'product_qty': 1,    
                                    'product_uom': product_obj.uom_id.id,                             
                                    'price_unit': abs(line.debit-line.credit),
                                    'order_id': purchase_order.id,
                                    'date_planned': datetime.now(), 
                                    'account_analytic_id': line.analytic_account_id.id if line.analytic_account_id else None,
                                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids if line.analytic_tag_ids else [])]                              
                                }
                            self.env['purchase.order.line'].sudo().create(commission_line)
                        
    def action_payslip_cancel(self):
        if self.filtered(lambda slip: slip.state == 'done'):
            raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        self.mapped('payslip_run_id').batch_set_draft()

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _check_duplicate_records(self):
        for slip in self:
            if slip.employee_id and slip.date_from and slip.date_to:
                # import pdb
                # pdb.set_trace()
                payslip_month=int(self.month)
                payslip_year = int(self.year)
                current_month = datetime.now().month
                current_year = datetime.now().year
                
#                 if payslip_month not in (current_month,current_month-1) or payslip_year != current_year:
#                     raise UserError(_('Payslip can generate within %s and %s in %s' %(calendar.month_name[current_month-1],calendar.month_name[current_month],current_year)))

                
                if self.search([('employee_id', '=', slip.employee_id.id),
                                ('date_from', '=', slip.date_from),
                                ('date_to', '=', slip.date_to),
                                ('id', '<>', self.id)]):
                    
                    raise UserError(_('Payslip No %s for %s has already generated on the selected month.' % (slip.number,slip.employee_id.name)))


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    loan_line_ids = fields.Many2many('hr.loan.line', 'payslip_input_loan_line_rel', 'payslip_input_id', 'loan_line_id', string="Loan Installment", help="Loan installment")
    insurance_line_ids = fields.Many2many('hr.insurance.line', 'payslip_input_insurance_line_rel', 'payslip_input_id', 'insurance_line_id', string="Insurance Installment")


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    @api.model
    def _domain_company_id(self):
        if self.env.context.get('allowed_company_ids'):
            return "[('id', 'in', %s)]" % self.env.context['allowed_company_ids']
        return "[]"

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company,
                                 states={'draft': [('readonly', False)]}, domain=lambda self: self._domain_company_id())
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure')
    year = fields.Selection(selection='_get_selection', string='Year', default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', default=lambda x: str(datetime.now().month))

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_start = date(year=int(self.year), month=int(self.month), day=1)
            self.date_end = date(year=int(self.year), month=int(self.month), day=monthrange(int(self.year), int(self.month))[1])

    @api.onchange('date_start', 'date_end')
    def onchange_date_start_and_end(self):
        if self.date_start and self.date_end:
            fiscal_year = self.env['account.fiscal.year'].search([('date_from', '<=', self.date_start),
                                                                  ('date_to', '>=', self.date_end)])
            if not fiscal_year:
                action = self.env.ref('account.actions_account_fiscal_year')
                raise RedirectWarning(_('You should configure a Fiscal Year first.'), action.id, _('Fiscal Years'))

    def action_set_to_draft(self):
        return self.write({'state': 'draft'})
    
    def batch_set_draft(self):
        if all(slip.state == 'cancel' for slip in self.mapped('slip_ids')):
            self.write({'state': 'draft'})


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _get_available_contracts_domain(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        domain = [('contract_ids.state', '=', 'open'), ('company_id', '=', company_id)]
        return self._get_available_contracts_company_domain()   

    def _get_available_contracts_company_domain(self):        
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        domain = [('contract_ids.state', '=', 'open'), ('company_id', '=', company_id)]
        self.env.context.get('structure_id')
        print("new method")
        contract_ids = self.env['hr.contract'].search([('state','=','open'), ('company_id', '=', company_id)])
        if self._context.get('default_structure_id'):
            contract_ids = self.env['hr.contract'].search([('state','=','open'), ('company_id', '=', company_id),('struct_id','=',self._context.get('default_structure_id'))])
        emp_ids = []
        if  contract_ids:
            for contract in contract_ids:  
                emp_ids.append(contract.employee_id.id)
        
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            to_date = fields.Date.to_date(self.env.context.get('default_date_end'))
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
            from_date = payslip_run.date_start
            to_date = payslip_run.date_end
        employee_ids = self.env['hr.employee'].sudo().search([('resign_date','!=',False),('company_id', '=', company_id),'|',('active','=',False),('active','=',True)])
        for emp_id in employee_ids:
            if to_date.month <= emp_id.resign_date.month  and to_date.year <= emp_id.resign_date.year:            
                for contract in self.env['hr.contract'].search([('state', 'in', ['open','close']),('employee_id','=',emp_id.id),('active','=',False), ('company_id', '=', company_id),('struct_id','=',self._context.get('default_structure_id'))],order="id desc",limit=1):
                    contract.employee_id.write({'active':True})
                    if contract.employee_id.id == 5115:
                        print(emp_id.id)
                    emp_ids.append(contract.employee_id.id)            
                         
            
        print("employee")
        print(emp_ids)
        domain = [('id', 'in', emp_ids)]
        print(domain)  
        return domain

    def _get_employees_company_domain(self):
        # YTI check dates too
        return self.env['hr.employee'].search(self._get_available_contracts_company_domain())
        
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
                                    default=lambda self: self._get_employees_company_domain(), domain=lambda self: self._get_available_contracts_company_domain(), required=True)
    company_id = fields.Many2one('res.company', 'Company')

    @api.onchange('structure_id')
    def onchange_structure_id(self):
        #domain = self._get_available_contracts_domain()
        domain = self._get_available_contracts_company_domain()        
#         if self.structure_id:
#             domain += [('contract_ids.struct_id', '=', self.structure_id.id)]
            # self.employee_ids = False
        # self.employee_ids = [(6, 0, self.env['hr.employee'].search(domain).ids)]
        return {'domain': {'employee_ids': domain}}

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        print("Employees : ", self.employee_ids.ids)
        for emp in self.employee_ids.ids:
            if emp == 5222:
                print(emp)
        contracts = self.employee_ids._get_contracts(payslip_run.date_start, payslip_run.date_end, states=['open'])
        
        employee_ids = self.env['hr.employee'].search([('resign_date','>',payslip_run.date_start),('company_id','=',self._context.get('default_company_id'))])
        for emp in employee_ids:           
            #for emp in self.env['hr.employee'].search([('id','in',[emp_id.id]),('resign_date','>',payslip_run.date_start)]):
            if payslip_run.date_end.month <= emp.resign_date.month and payslip_run.date_end.year <= emp.resign_date.year:            
                contract_id = self.env['hr.contract'].search(
                expression.AND([[('employee_id', '=', emp.id),('company_id','=',self._context.get('default_company_id')),('struct_id','=',self._context.get('default_structure_id'))],
                [('state', 'in', ['open','close'])],
                [('date_start', '<=', payslip_run.date_end),
                    '|',
                        ('date_end', '=', False),
                        ('date_end', '>=', payslip_run.date_start)]]),order="id desc",limit=1)
                if contract_id:
                    contracts += contract_id
                else:
                    contract_id = self.env['hr.contract'].search(
                    expression.AND([[('employee_id', '=', emp.id),('struct_id','=',self._context.get('default_structure_id'))],
                    [('state', 'in', ['open','close'])],
                    [('date_start', '<=', payslip_run.date_end),                
                            ('date_end', '>=', payslip_run.date_start),('active','=',False)]]),order="id desc",limit=1)
                    if contract_id:
                        contracts += contract_id  
                        print("contract added>>>>") 
                emp.write({'active':False})        
        # contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        # work_entries = self.env['hr.work.entry'].search([
        #     ('date_start', '<=', payslip_run.date_end),
        #     ('date_stop', '>=', payslip_run.date_start),
        #     ('employee_id', 'in', self.employee_ids.ids),
        # ])
        
        # self._check_undefined_slots(work_entries, payslip_run)

        # validated = work_entries.action_validate()
        # if not validated:
        #     raise UserError(_("Some work entries could not be validated."))

        print("Contracts : ", contracts)
        default_values = Payslip.default_get(Payslip.fields_get())
        for contract in contracts:
            if contract.id == 14726:
                print("hello")
            date_start = payslip_run.date_start
            date_end = payslip_run.date_end

            if contract.date_start and contract.date_start > date_start:
                date_start = contract.date_start

            if contract.date_end and contract.date_end < date_end:
                date_end = contract.date_end

            values = dict(default_values, **{
                'employee_id': contract.employee_id.id,
                'credit_note': payslip_run.credit_note,
                'payslip_run_id': payslip_run.id,
                'month': payslip_run.month,
                'year': payslip_run.year,
                'date_from': date_start,
                'date_to': date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.struct_id.id or contract.structure_type_id.default_struct_id.id,
            })
            last_month = date_start + timedelta(days=-1)
            last_month_slip = self.env['hr.payslip'].search(
                [('date_to', '=', last_month), ('employee_id', '=', contract.employee_id.id),('state','=','done')], limit=1)
            if not last_month_slip:
                if contract.employee_id.joining_date.month != date_start.month and contract.employee_id.joining_date.year == date_start.year:
                    raise ValidationError(
                        _('%s Payroll not allowed skip month. Payslip month must be run incremental') % (contract.employee_id.name))

            payslip = self.env['hr.payslip'].new(values)
            payslip._onchange_employee()
            values = payslip._convert_to_write(payslip._cache)
            payslips += Payslip.create(values)
        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
