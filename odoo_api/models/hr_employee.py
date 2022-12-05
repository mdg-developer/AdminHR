from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from twilio.rest import Client
from pytz import timezone, UTC
from datetime import datetime, date, time, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
import pyotp
from odoo.tools import float_compare, DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
import math
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import MobileApplicationClient
import urllib.parse as urlparse
from urllib.parse import parse_qs
from requests.structures import CaseInsensitiveDict
import requests
from odoo.addons.hr_attendance_ext.models.hr_attendance import time_to_float

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
    return value.hour + value.minute / 60 + value.second / 3600

class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    def check_employee_role(self, employee_id=None):
        employee = self.env['hr.employee'].sudo().search(['|', '|', ('parent_id', '=', employee_id),
                                                          ('approve_manager', '=', employee_id),
                                                          ('branch_id.manager_id', '=', employee_id)])
        driver = self.env['fleet.vehicle'].sudo().search([('hr_driver_id', '=', employee_id)])
        spare = self.env['fleet.vehicle'].sudo().search([('spare_id', '=', employee_id)])
        branch_manager = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        dotted_line_manager = self.env['hr.employee'].sudo().search([('dotted_line_manager_id', '=', employee_id)])
        if employee:
            if branch_manager:
                if dotted_line_manager:
                    if driver:
                        if spare:
                            return "manager,branch manager,dotted_line_manager,driver,spare"
                        else:
                            return "manager,branch manager,dotted_line_manager,driver"
                    else:
                        if spare:
                            return "manager,branch manager,dotted_line_manager,spare"
                        else:
                            return "manager,branch manager,dotted_line_manager"
                else:
                    if driver:
                        if spare:
                            return "manager,branch manager,driver,spare"
                        else:
                            return "manager,branch manager,driver"
                    else:
                        if spare:
                            return "manager,branch manager,spare"
                        else:
                            return "manager,branch manager"
            else:
                if dotted_line_manager:
                    if driver:
                        if spare:
                            return "manager,dotted_line_manager,driver,spare"
                        else:
                            return "manager,dotted_line_manager,driver"
                    else:
                        if spare:
                            return "manager,dotted_line_manager,spare"
                        else:
                            return "manager,dotted_line_manager"
                else:
                    if driver:
                        if spare:
                            return "manager,driver,spare"
                        else:
                            return "manager,driver"
                    else:
                        if spare:
                            return "manager,spare"
                        else:
                            return "manager"
        else:
            if branch_manager:
                if dotted_line_manager:
                    if driver:
                        if spare:
                            return "branch manager,dotted_line_manager,driver,spare"
                        else:
                            return "branch manager,dotted_line_manager,driver"
                    else:
                        if spare:
                            return "branch manager,dotted_line_manager,spare"
                        else:
                            return "branch manager,dotted_line_manager"
                else:
                    if driver:
                        if spare:
                            return "branch manager,employee,driver,spare"
                        else:
                            return "branch manager,employee,driver"
                    else:
                        if spare:
                            return "branch manager,employee,spare"
                        else:
                            return "branch manager,employee"
            else:
                if dotted_line_manager:
                    if driver:
                        if spare:
                            return "dotted_line_manager,driver,spare"
                        else:
                            return "dotted_line_manager,driver"
                    else:
                        if spare:
                            return "dotted_line_manager,spare"
                        else:
                            return "dotted_line_manager"
                else:
                    if driver:
                        if spare:
                            return "employee,driver,spare"
                        else:
                            return "employee,driver"
                    else:
                        if spare:
                            return "employee,spare"
                        else:
                            return "employee"

    def check_in(self, fingerprint_id=None, employee_id=None, check_in=None, check_out=None, latitude=None, longitude=None):
        attendance_obj = self.env['hr.attendance.raw']

        if check_in:
            input_datetime = check_in
        if check_out:
            input_datetime = check_out
                
        if fingerprint_id and employee_id:   
            employee = self.env['hr.employee'].search([('fingerprint_id', '=', fingerprint_id),
                                                       ('id', '=', employee_id)])
            if employee:
                attendance_vals = {"fingerprint_id": fingerprint_id,
                                   "employee_name": employee.name,
                                   "employee_id": employee_id,
                                   "attendance_datetime": input_datetime,
                                   "action": 'check_in' if check_in else 'check_out',
                                   "source": "via Mobile App",
                                   "latitude": latitude,
                                   "longitude": longitude,
                                   }
                attendance_obj.create(attendance_vals)
                return True
        return False
                    
    def get_employees(self, employee_id=None):
        if employee_id:
            employee = self.env['hr.employee'].sudo().search(['|', '|', '|', ('parent_id', '=', employee_id),
                                                              ('dotted_line_manager_id', '=', employee_id),
                                                              ('approve_manager', '=', employee_id),
                                                              ('branch_id.manager_id', '=', employee_id)])
            if employee:
                return employee.ids + [employee_id]
            else:
                return [employee_id]
                
    def get_leave_report(self, employee_id=None):
        
        if employee_id:
            employee = self.env['hr.employee'].search([('approve_manager', '=', employee_id)])
            if employee:
                self.env.cr.execute("""select * from x_bi_sql_view_leave_report where (x_employee_id in %s or x_employee_id=%s) order by x_name,x_leave_type;""", (tuple(employee.ids),employee_id,))
                leaves = self.env.cr.dictfetchall()
                if leaves:
                    return leaves
            else:
                self.env.cr.execute("""select * from x_bi_sql_view_leave_report where x_employee_id=%s order by x_name,x_leave_type;""", (employee_id,))
                leaves = self.env.cr.dictfetchall()
                if leaves:
                    return leaves
                
    def change_password(self, employee_id=None, old_pwd=None, new_pwd=None):
        
        if old_pwd and new_pwd:
            employee = self.env['hr.employee'].search([('id', '=', employee_id),('pin', '=', old_pwd)])
            if employee:
                vals = { "pin": new_pwd }
                emp_obj = self.env['hr.employee'].browse(employee.id)
                emp_obj.write(vals)
                return True 
            else:
                raise ValidationError(_("Old password is not correct."))
        
    def sign_in(self, barcode=None, pin=None):
        print("barcode : ", barcode)
        print("pin : ", pin)
        if barcode and pin:
            print("YESSSS")
            employee = self.env['hr.employee'].sudo().search([('barcode', '=', barcode),('pin', '=', pin)], limit=1)
            print("employee : ", employee)
            if employee:
                print("employee exists")
                vals = {"employee_id": employee.id}
                return vals
            else:
                return {"employee_id": 0} #return value to app employee not found
    
    def send_sms(self, phone=None, message=None):
        
        access_token = None
        consumer_key = self.env['ir.config_parameter'].sudo().get_param('telenor_consumer_key')
        consumer_secret = self.env['ir.config_parameter'].sudo().get_param('telenor_consumer_secret')
        auth_url = 'https://prod-apigw.mytelenor.com.mm/oauth/v1/userAuthorize?client_id=%s&response_type=code&scope=READ'%(consumer_key)
        scopes = ['READ']
        oauth = OAuth2Session(client=MobileApplicationClient(client_id=consumer_key), scope=scopes)
        authorization_url, state = oauth.authorization_url(auth_url)
        response = oauth.get(authorization_url)
        response_url = response.url
        parsed = urlparse.urlparse(response_url)
        code = parse_qs(parsed.query)['code']
        auth_code = code[0]
        
        token_url = "https://prod-apigw.mytelenor.com.mm/oauth/v1/token"
        token_headers = CaseInsensitiveDict()
        token_headers["Content-Type"] = "application/x-www-form-urlencoded"
        token_data = "grant_type=authorization_code&client_id=%s&client_secret=%s&expires_in=86400&code=%s&redirect_uri=https://www.wbholdings.biz/oauth2/callback" %(consumer_key,consumer_secret,auth_code,)
        
        resp = requests.post(token_url, headers=token_headers, data=token_data)
        if resp.status_code == 200:
            result = resp.json()
            access_token = result['accessToken']
                    
        sms_url = "https://prod-apigw.mytelenor.com.mm/v3/mm/en/communicationMessage/send"
        sms_headers = CaseInsensitiveDict()
        sms_headers["Authorization"] = "Bearer " + access_token
        sms_headers["Content-Type"] = "application/json"
        
        sms_data = """           
        {
           "type": "TEXT",
           "content": "%s",
           "characteristic": [         
              {
                 "name": "UserName",
                 "value": "B2BWinBro"
              },
              {
                 "name": "Password",
                 "value": "B2BWin"
              }
           ],
           "sender": {
              "@type": "5",
              "name": "WINBROTHERS"
           },
           "receiver": [
              {
                 "@type": "1",
                 "phoneNumber": "%s"
              }
           ]
        }
        """ %(message,phone,)        
        requests.post(sms_url, headers=sms_headers, data=sms_data)
                    
    def forget_password(self, barcode=None):
        
        if barcode:
            employee = self.env['hr.employee'].search([('barcode', '=', barcode)])
            if employee:
                totp = pyotp.TOTP('base32secretboc')
                otp = totp.now()
                print("opt code:%s", otp);
                otp_message = "%s is your One Time Pin (OTP) code." %(otp,)       
                                
                mobile = employee.mobile_phone
                if mobile:              
                    if mobile.startswith('09-') or mobile.startswith('09'):
                        if mobile.startswith('09-'):
                            phone = '959' + str(mobile[3:])  
                        else:
                            phone = '959' + str(mobile[2:])
                    if mobile.startswith('+959'):  
                        phone = '959' + str(mobile[4:])        
                    employee.send_sms(phone=phone,message=otp_message)
                    vals = {'pin': otp}
                    emp_obj = self.env['hr.employee'].browse(employee.id)
                    emp_obj.write(vals)  
                    return otp                                
                else:
                    raise ValidationError(_(
                        "Please enter mobile number for employee."))

    def approval_summary_requests(self, employee_id=None, state='submit'):
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        request_obj = self.env['summary.request'].with_context(employee_id=employee_id)
        requests = request_obj.sudo().search([('state', '=', state), ('start_date', '>=', date_range[0]), ('start_date', '<=', date_range[1])])
        return requests.filtered(lambda r: r.enable_approval).ids
    
    def get_leave_type(self,employee_id):
        employee_id = int(employee_id) or self.id
        employee_id = self.env['hr.employee'].search([('id','=',employee_id)])
        results = []
        leave_types = []
        val = {}
        if employee_id:
            domain = ['&', ('virtual_remaining_leaves', '>', 0), '|', ('allocation_type', 'in', ['fixed_allocation', 'no']),'&',('allocation_type', '=', 'fixed'), ('max_leaves', '>', '0')]
        
            contract = self.env['hr.contract'].search([('employee_id','=',employee_id.id),('state','=','open')],order='id desc', limit=1)
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
                for leave_id in self.env['hr.leave.type'].search([('id','in',leave_types)],order='code asc'):
                    results.append({'id': leave_id.id,
                                    'name': leave_id.name,
                                    'show_in_mobile_app': leave_id.show_in_mobile_app})
            else:
                leave_types = []
                leaves = self.env['hr.leave.type'].search(domain)
                for leave in leaves:
                    leave_types.append(leave.id)
                if employee_id.resource_calendar_id.one_day_off == True or contract.resource_calendar_id.no_holidays == True:
                    domain = ['|', ('one_day_off','=',True), ('no_holidays','=',True)]
                    leaves = self.env['hr.leave.type'].search(domain)
                    for leave in leaves:
                        leave_types.append(leave.id)
                for leave_id in self.env['hr.leave.type'].search([('id','in',leave_types)],order='code asc'):
                    results.append({'id': leave_id.id,
                                    'name': leave_id.name,
                                    'show_in_mobile_app': leave_id.show_in_mobile_app})
        val ={'result':results}
        return val
    
    def approval_summary_requests_count(self, employee_id=None, state='submit'):
        result = self.approval_summary_requests(employee_id)
        return len(result)

    def get_md_ids(self):
        result = []
        all_companies = self.env['res.company'].sudo().search([])
        for company in all_companies:
            if company.managing_director_id.id not in result:
                result.append(company.managing_director_id.id)
        return result
        
    def approval_travel_requests(self, employee_id=None, state='submit'):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        requests = self.env['travel.request']
        domain = [('state', '=', state), ('start_date', '>=', date_range[0]), ('start_date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            print("Branch Manager")
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            requests = requests.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            print("Both branch and direct mgr")
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            requests = requests.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            print("Only direct mgr")
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            requests = requests.sudo().search(domain)
        elif managing_director_companies:
            print("MD")
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            print("branches : ", branches)
            print("branch managers : ", branch_mgr_ids)
            print("domain : ", domain)
            requests = requests.sudo().search(domain)
        if requests:
            for request in requests:
                result.append(request.id)
        return result
        
    def approval_travel_requests_count(self, employee_id=None, state='submit'):
        employee_id = int(employee_id) or int(self.id)
        result = self.approval_travel_requests(employee_id)
        return len(result)
    
    def approved_travel_requests(self, employee_id=None, state=None):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        requests = self.env['travel.request']
        domain = [('state', 'in', ['approve','advance_request','advance_withdraw','in_progress','done','verify']), ('start_date', '>=', date_range[0]), ('start_date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            requests = requests.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            requests = requests.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            requests = requests.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            requests = requests.sudo().search(domain)
        if requests:
            for request in requests:
                result.append(request.id)
        return result
        
    def approved_travel_requests_count(self, employee_id=None, state=None):
        employee_id = int(employee_id) or int(self.id)
        result = self.approved_travel_requests(employee_id)
        return len(result)
        
    def approval_out_of_pocket_expense(self, employee_id=None, state='submit'):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        expenses = self.env['hr.pocket.expense']
        domain = [('state', '=', state), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        if expenses:
            for expense in expenses:
                result.append(expense.id)
        return result
    
    def approval_out_of_pocket_expense_count(self, employee_id=None, state='submit'):
        employee_id = int(employee_id) or int(self.id)
        result = self.approval_out_of_pocket_expense(employee_id)
        return len(result)
    
    def approved_out_of_pocket_expense(self, employee_id=None, state=None):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        expenses = self.env['hr.pocket.expense']
        domain = [('state', 'in', ['approve','finance_approve','reconcile']), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        if expenses:
            for expense in expenses:
                result.append(expense.id)
        return result
    
    def approved_out_of_pocket_expense_count(self, employee_id=None, state=None):
        employee_id = int(employee_id) or int(self.id)
        result = self.approved_out_of_pocket_expense(employee_id)
        return len(result)
    
    def approval_travel_expense(self, employee_id=None, state='submit'):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        expenses = self.env['hr.travel.expense']
        domain = [('state', '=', state), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        if expenses:
            for expense in expenses:
                result.append(expense.id)
        return result
    
    def approval_travel_expense_count(self, employee_id=None, state='submit'):
        employee_id = int(employee_id) or int(self.id)
        result = self.approval_travel_expense(employee_id)
        return len(result)
    
    def approved_travel_expense(self, employee_id=None, state=None):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        expenses = self.env['hr.travel.expense']
        domain = [('state', 'in', ['approve','finance_approve','reconcile']), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        if expenses:
            for expense in expenses:
                result.append(expense.id)
        return result
    
    def approved_travel_expense_count(self, employee_id=None, state=None):
        employee_id = int(employee_id) or int(self.id)
        result = self.approved_travel_expense(employee_id)
        return len(result)
    
    def approval_trip_expense(self, employee_id=None, state='submit'):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        expenses = self.env['admin.trip.expense']
        domain = [('state', '=', state), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        if expenses:
            for expense in expenses:
                result.append(expense.id)
        return result
    
    def approval_trip_expense_count(self, employee_id=None, state='submit'):
        employee_id = int(employee_id) or int(self.id)
        result = self.approval_trip_expense(employee_id)
        return len(result)
    
    def approved_trip_expense(self, employee_id=None, state=None):
        result = []
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        expenses = self.env['admin.trip.expense']
        domain = [('state', 'in', ('approve', 'finance_approve')), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
        branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
        direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
        managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
        md_ids = self.get_md_ids()
        if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
            domain += [('employee_id', '!=', employee_id),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                             ('manager_id', 'not in', md_ids)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += [('employee_id', '!=', employee_id),
                       ('employee_id', 'in', branch_mgr_ids)]
            expenses = expenses.sudo().search(domain)
        elif managing_director_companies:
            branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
            branch_mgr_ids = [x.manager_id.id for x in branches]
            domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                    ('employee_id.branch_id.manager_id', '=', employee_id)]
            expenses = expenses.sudo().search(domain)
        if expenses:
            for expense in expenses:
                result.append(expense.id)
        return result
    
    def approved_trip_expense_count(self, employee_id=None, state=None):
        employee_id = int(employee_id) or int(self.id)
        result = self.approved_trip_expense(employee_id)
        return len(result)
    
    def approval_overtime_count(self, employee_id=None, requested_employee_id=None, state='draft'):
        if employee_id:
            employee_id = int(employee_id) or int(self.id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            start_date = date_range[0] + ' 00:00:00'
            end_date = date_range[1] + ' 23:59:59'
            request_obj = self.env['ot.request.line']
            requests = request_obj.sudo().search([('employee_id', '=', employee_id), ('state', '=', state), ('start_date', '>=', start_date), ('start_date', '<=', end_date)])
            return len(requests)
        if requested_employee_id:
            requested_employee_id = int(requested_employee_id)
            employee = self.env['hr.employee'].sudo().browse(requested_employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            start_date = date_range[0] + ' 00:00:00'
            end_date = date_range[1] + ' 23:59:59'
            request_obj = self.env['ot.request.line'] 
            requests = request_obj.sudo().search([('requested_employee_id', '=', requested_employee_id), ('state', '=', state), ('start_date', '>=', start_date), ('start_date', '<=', end_date)])
            return len(requests)

    def approval_attendance(self, employee_id=None, state='draft'):
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        request_obj = self.env['hr.attendance'].with_context(employee_id=employee_id)
        self.env.cr.execute("""select att.id
                            from hr_attendance att,hr_employee he
                            where att.employee_id=he.id
                            and att.state=%s
                            and check_in::date >= %s
                            and check_in::date <= %s
                            and (he.no_need_attendance!=True or he.no_need_attendance is null)
                            and (att.is_absent=True or att.late_minutes>0 or att.early_out_minutes>0 or att.missed=True);""", (state,date_range[0],date_range[1]))
        attendance = set(res[0] for res in self.env.cr.fetchall())
        if attendance:
            attendances = request_obj.sudo().search([('id', 'in', tuple(attendance))])
            if attendances:                
                return attendances.filtered(lambda r: r.enable_approval).ids

    def approval_loan(self, employee_id=None, state='waiting_approval_1'):
        employee_id = int(employee_id) or int(self.id)
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        date_range = self.get_fiscal_year(employee.company_id.id)
        request_obj = self.env['hr.loan'].with_context(employee_id=employee_id)
        requests = request_obj.sudo().search([('state', '=', state), 
                                            ('date', '>=', date_range[0]), 
                                            ('date', '<=', date_range[1])])
        return requests.filtered(lambda r: r.enable_approval).ids
    
    def get_travel_request(self, employee_id=None):
        self.env.cr.execute("""select id, name, start_date, end_date from travel_request where state not in ('draft','submit','cancel') and employee_id=%s;""", (employee_id,))
        requests = self.env.cr.dictfetchall()
        if requests:
            return requests

    def get_attendance_history(self, employee_id=None):
        employee_id = employee_id or self.id
        emp_list = self.search([('approve_manager', '=', employee_id),('no_need_attendance', '!=', True)], order='name asc')
        att_obj = self.env['hr.attendance'].sudo()
        history = []
        for emp in emp_list:
            tz = timezone(emp.tz or 'Asia/Yangon')
            last_attend = att_obj.search([('employee_id', '=', emp.id)], order='check_in desc', limit=1)
            if last_attend:
                last_date = UTC.localize(last_attend.check_in, is_dst=True).astimezone(tz=tz)
                month_start = datetime.combine(last_date.date().replace(day=1), datetime.min.time())
                search_date = tz.localize(month_start.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
                count = att_obj.search_count([('employee_id', '=', emp.id), ('check_in', '>=', search_date)])
                history.append({'employee_id': emp.id, 'employee_name': emp.name, 'count': count, 'search_date': search_date.strftime(DT)})
            else:
                todayDate = datetime.now(tz).date()
                month_start = datetime.combine(todayDate.replace(day=1), datetime.min.time())
                search_date = tz.localize(month_start.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
                history.append({'employee_id': emp.id, 'employee_name': emp.name, 'count': 0, 'search_date': search_date.strftime(DT)})
        return history
    
    def check_valid_leaves(self, employee_id=None, holiday_status_id=None, start_date=None, end_date=None, duration=None, description=None, attachment=None, leave_line=None):
        leave_type = self.env['hr.leave.type'].browse(holiday_status_id)
        employee = self.env['hr.employee'].browse(employee_id)
        for leave in leave_line:
            if not leave.get('full') and not leave.get('first') and not leave.get('second'):
                return {'status': 'error', 'message': 'Please Choose which part of the day to request leave!'}            
        if leave_type.allocation_type != 'no':
            mapped_days = leave_type.get_employees_leave_days(employee.ids)
            leave_days = mapped_days[employee_id][holiday_status_id]
            no_of_leaves = duration            
            if float_compare(leave_days['remaining_leaves'], no_of_leaves, precision_digits=2) == -1 or float_compare(leave_days['virtual_remaining_leaves'], no_of_leaves, precision_digits=2) == -1:
                return {'status': 'error', 'message': 'The number of remaining time off is not sufficient for this time off type. Please also check the time off waiting for validation.'}
        for line in leave_line:
            domain = [('start_date', '<', line.get('end_date')), ('end_date', '>', line.get('start_date')),
                      ('employee_id', '=', employee_id), ('state', 'not in', ('cancel', 'refuse'))]
            if self.env['summary.request'].search(domain):                
                return {'status': 'error', 'message': 'You can not set 2 times off that overlaps on the same day for the same employee.'}
        return {'status': 'success', 'message': 'Requested leaves are valid!'}
    
    def approval_warning_count(self, employee_id=None):
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            warning_obj = self.env['hr.warning']
            warnings = warning_obj.sudo().search([('employee_id.branch_id.manager_id.id', '=', employee_id), 
                                                ('state', '=', 'submit'), 
                                                ('date', '>=', date_range[0]), 
                                                ('date', '<=', date_range[1])])
            return len(warnings)

   
        
    def approval_reward_count(self, employee_id=None):
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            reward_obj = self.env['hr.reward']
            rewards = reward_obj.sudo().search([('employee_id.branch_id.manager_id.id', '=', employee_id), 
                                                ('state', '=', 'submit'), 
                                                ('date', '>=', date_range[0]), 
                                                ('date', '<=', date_range[1])])
            return len(rewards)
        
    def get_documents(self, employee_id=None):
        
        if employee_id:
            employee_id = int(employee_id)
            self.env.cr.execute("""select distinct docs.id document_id,docs.name document_name,folder.id folder_id,folder.name folder_name,attachment.mimetype file_type
                                from documents_folder_read_groups doc_rel,res_groups_users_rel user_rel,
                                hr_employee he,documents_document docs,documents_folder folder,ir_attachment attachment
                                where doc_rel.res_groups_id=user_rel.gid
                                and user_rel.uid=he.user_id
                                and doc_rel.documents_folder_id=docs.folder_id
                                and doc_rel.documents_folder_id=folder.id
                                and docs.attachment_id=attachment.id
                                and docs.active=true
                                and he.id=%s""", (employee_id,))
            documents_folder = self.env.cr.dictfetchall()
            if documents_folder:
                return documents_folder
            
    def get_folders(self, employee_id=None):
        
        if employee_id:
            employee_id = int(employee_id)
            self.env.cr.execute("""select distinct folder.id folder_id,folder.name folder_name
                                from documents_folder_read_groups doc_rel,res_groups_users_rel user_rel,
                                hr_employee he,documents_document docs,documents_folder folder
                                where doc_rel.res_groups_id=user_rel.gid
                                and user_rel.uid=he.user_id
                                and doc_rel.documents_folder_id=docs.folder_id
                                and doc_rel.documents_folder_id=folder.id
                                and he.id=%s""", (employee_id,))
            folders = self.env.cr.dictfetchall()
            if folders:
                return folders
            
    def get_announcement_ids(self, employee_id=None):
        
        if employee_id:            
            now = datetime.now()
            now_date = now.date()
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].browse(employee_id)
            ann_ids_general = self.env['hr.announcement'].sudo().search([('is_announcement', '=', True),
                                                                         ('state', 'in', ('approved', 'done')),
                                                                         ('date_start', '<=', now_date),
                                                                         ('date_end', '>=', now_date)])
            ann_ids_emp = self.env['hr.announcement'].search([('employee_ids', 'in', [employee.id]),
                                                              ('announcement_type', '=', 'employee'),
                                                              ('state', 'in', ('approved', 'done')),
                                                              ('date_start', '<=', now_date),
                                                              ('date_end', '>=', now_date)])
            ann_ids_dep = self.env['hr.announcement'].sudo().search([('department_ids', 'in', [employee.department_id.id]),
                                                                     ('announcement_type', '=', 'department'),
                                                                     ('state', 'in', ('approved', 'done')),
                                                                     ('date_start', '<=', now_date),
                                                                     ('date_end', '>=', now_date)])
            ann_ids_job = self.env['hr.announcement'].sudo().search([('job_grade_ids', 'in', [employee.contract_id.job_grade_id.id]),
                                                                     ('announcement_type', '=', 'job_grade'),
                                                                     ('state', 'in', ('approved', 'done')),
                                                                     ('date_start', '<=', now_date),
                                                                     ('date_end', '>=', now_date)])
            ann_ids_company = self.env['hr.announcement'].sudo().search([('announcement_company_id', '=', employee.company_id.id),
                                                                         ('is_announcement', '=', False),
                                                                         ('announcement_type', '=', False),
                                                                         ('state', 'in', ('approved', 'done')),
                                                                         ('date_start', '<=', now_date),
                                                                         ('date_end', '>=', now_date)])
            return ann_ids_general.ids + ann_ids_emp.ids + ann_ids_dep.ids + ann_ids_job.ids + ann_ids_company.ids
        
    def approval_announcements(self, employee_id=None):
        lists = []
        announcements = self.env['hr.announcement']
        if employee_id: 
            employee_id = int(employee_id)     
            employee_obj = self.env['hr.employee'].sudo().browse(employee_id)   
            date_range = self.get_fiscal_year(employee_obj.company_id.id)
            companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if companies:
                for company in companies:
                    announcements += self.env['hr.announcement'].sudo().search([('announcement_company_id', '=', company.id),
                                                                                ('state', '=', 'to_approve'),
                                                                                ('date_start', '>=', date_range[0]),
                                                                                ('date_start', '<=', date_range[1])])
                if employee_obj.name == 'Htun Win':
                    announcements += self.env['hr.announcement'].sudo().search([('state', '=', 'to_approve'), 
                                                                                ('is_announcement', '=', True),
                                                                                ('date_start', '>=', date_range[0]),
                                                                                ('date_start', '<=', date_range[1])])
                if announcements:
                    for data in announcements:
                        lists.append(data.id)  
        return lists  
    
    def approved_announcements(self, employee_id=None):
        lists = []
        announcements = self.env['hr.announcement']
        if employee_id: 
            employee_id = int(employee_id)         
            employee_obj = self.env['hr.employee'].sudo().browse(employee_id)   
            date_range = self.get_fiscal_year(employee_obj.company_id.id)
            companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if companies:
                for company in companies:
                    announcements += self.env['hr.announcement'].sudo().search([('announcement_company_id', '=', company.id),
                                                                                ('state', '=', 'approved'),
                                                                                ('date_start', '>=', date_range[0]),
                                                                                ('date_start', '<=', date_range[1])])
                if employee_obj.name == 'Htun Win':
                    announcements += self.env['hr.announcement'].sudo().search([('state', '=', 'approved'), 
                                                                                ('is_announcement', '=', True),
                                                                                ('date_start', '>=', date_range[0]),
                                                                                ('date_start', '<=', date_range[1])])
                if announcements:
                    for data in announcements:
                        lists.append(data.id)  
        return lists  
    
    def approval_announcements_count(self, employee_id=None):
        result = self.approval_announcements(employee_id)
        return len(result)
    
    def approval_routes(self, employee_id=None): 
        lists = []
        if employee_id:
            employee_id = int(employee_id) 
            employee = self.env['hr.employee'].sudo().browse(employee_id)   
            date_range = self.get_fiscal_year(employee.company_id.id)
            branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            if branches:
                companies = [x.company_id.id for x in branches]
                routes = self.env['route.plan'].sudo().search([('company_id', 'in', companies),
                                                               ('branch_id', 'in', branches.ids),
                                                               ('state', '=', 'submit'),
                                                               ('start_date', '>=', date_range[0]),
                                                               ('start_date', '<=', date_range[1])])
                if routes:
                    for route in routes:
                        lists.append(route.id)
            return lists
    
    def approval_route_count(self, employee_id=None):
        result = self.approval_routes(employee_id)
        return len(result)

    def approved_routes(self, employee_id=None): 
        lists = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)   
            date_range = self.get_fiscal_year(employee.company_id.id)
            branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            if branches:
                companies = [x.company_id.id for x in branches]
                routes = self.env['route.plan'].sudo().search([('company_id', 'in', companies),
                                                               ('branch_id', 'in', branches.ids),
                                                               ('state', 'in', ('approve', 'decline')),
                                                               ('start_date', '>=', date_range[0]),
                                                               ('start_date', '<=', date_range[1])])
                if routes:
                    for route in routes:
                        lists.append(route.id)
            return lists

    def get_day_trip_lists(self, employee_id=None, state=None): 
        
        lists = []
        if employee_id:
            employee_id = int(employee_id)
            if state == 'running' or state == 'close' or state == 'expense_claim':
                driver = self.env['day.plan.trip'].sudo().search([('driver_id', '=', employee_id),
                                                                ('state', '=', state)])
                spare1 = self.env['day.plan.trip'].sudo().search([('spare1_id', '=', employee_id),
                                                                ('state', '=', state)])
                spare2 = self.env['day.plan.trip'].sudo().search([('spare2_id', '=', employee_id),
                                                                ('state', '=', state)])
                branch_manager = self.env['day.plan.trip'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id),
                                                                ('state', '=', state)])
            else:
                driver = self.env['day.plan.trip'].sudo().search([('driver_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                spare1 = self.env['day.plan.trip'].sudo().search([('spare1_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                spare2 = self.env['day.plan.trip'].sudo().search([('spare2_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                branch_manager = self.env['day.plan.trip'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id),
                                                                    ('state', 'in', ('draft', 'submit', 'open', 'advance_request', 'advance_withdraw', 'decline'))])
            if driver:
                for data in driver:
                    lists.append(data.id) 
            if spare1:
                for data in spare1:
                    lists.append(data.id)  
            if spare2:
                for data in spare2:
                    lists.append(data.id)  
            if branch_manager:
                for data in branch_manager:
                    lists.append(data.id)
            list_set = set(lists)
            unique_list = (list(list_set))
            return unique_list
    
    def get_plan_trip_product_lists(self, employee_id=None, state=None): 
        
        lists = []
        if employee_id and state:
            employee_id = int(employee_id) 
            if state == 'running' or state == 'close' or state == 'expense_claim':
                driver = self.env['plan.trip.product'].sudo().search([('driver_id', '=', employee_id),
                                                                ('state', '=', state)])
                spare1 = self.env['plan.trip.product'].sudo().search([('spare1_id', '=', employee_id),
                                                                ('state', '=', state)])
                spare2 = self.env['plan.trip.product'].sudo().search([('spare2_id', '=', employee_id),
                                                                ('state', '=', state)])
                branch_manager = self.env['plan.trip.product'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id),
                                                                ('state', '=', state)])
            else:
                driver = self.env['plan.trip.product'].sudo().search([('driver_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                spare1 = self.env['plan.trip.product'].sudo().search([('spare1_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                spare2 = self.env['plan.trip.product'].sudo().search([('spare2_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                branch_manager = self.env['plan.trip.product'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id),
                                                                    ('state', 'in', ('draft', 'submit', 'open', 'advance_request', 'advance_withdraw', 'decline'))])
            if driver:
                for data in driver:
                    lists.append(data.id) 
            if spare1:
                for data in spare1:
                    lists.append(data.id)  
            if spare2:
                for data in spare2:
                    lists.append(data.id)  
            if branch_manager:
                for data in branch_manager:
                    lists.append(data.id)
            list_set = set(lists)
            unique_list = (list(list_set))
            return unique_list
        
    def get_employee_payslip(self, employee_id=None):
        result = []
        total = net_total = 0
        if employee_id:
            employee_id = int(employee_id)
            today = fields.Date.today()
            fiscal_year = self.env['account.fiscal.year'].search([('date_from', '<=', today),
                                                                  ('date_to', '>=', today)],limit=1)

            for slip_id in self.env['hr.payslip'].sudo().search([('employee_id', '=', employee_id),('date_from','>=',fiscal_year.date_from),('date_to','<=',fiscal_year.date_to),
                                                                ('state', '=', 'done')], order='date_to desc'):
                self.env.cr.execute("""select distinct category_id from hr_payslip_line where slip_id= %s and amount > 0
                """,(slip_id.id,))
                results = self.env.cr.dictfetchall()
                category_line = [] 
                for res in results:
                    categ_id = res['category_id']
                    print("categ_id>>>>",categ_id)
                    catge_line_ids = []
                    category_name = ""
                    for slip_line in self.env['hr.payslip.line'].sudo().search([('slip_id', '=', slip_id.id),
                                                                                ('category_id','=',categ_id),
                                                                                ('amount','>',0)]):
                        category_name = slip_line.category_id.name
                        total += slip_line.total
                        if category_name =='Net':
                            net_total += slip_line.total
                        catge_line_ids.append({
                                                'name': slip_line.name,
                                                'code': slip_line.category_id.code,                            
                                                'total': slip_line.total
                                                    })
                    slip_category = {
                                     'name':category_name,
                                     'line_ids':catge_line_ids
                                     }
                    category_line.append(slip_category)
                    
                data = {
                        'id': slip_id.id,
                        'month': slip_id.date_from.strftime('%m'),
                        'year': slip_id.date_from.strftime('%Y'),
                        'date_from': slip_id.date_from.strftime('%Y-%m-%d'),
                        'date_to': slip_id.date_to.strftime('%Y-%m-%d'),
                        'total' : slip_line.total,
                        'employee_id': {
        
                        'id': slip_id.employee_id.id,
        
                        'name': slip_id.employee_id.name,
        
                        'job_id': {
        
                            'id': slip_id.employee_id.job_id.id,
        
                            'name': slip_id.employee_id.job_id.name,
        
                                  },
        
                        'department_id': {
        
                                    'id': slip_id.employee_id.department_id.id,        
                                    'name': slip_id.employee_id.department_id.name,
        
                                    }

                                },
                        'category_list':category_line
                        }
                result.append(data)
            
            res = {
                   'data':result
                   }
            
            return res    
        
    def get_plan_trip_waybill_lists(self, employee_id=None, state=None): 
        
        # lists = []
        # if employee_id and state:
        #     driver = self.env['plan.trip.waybill'].sudo().search([('driver_id', '=', employee_id),
        #                                                       ('state', '=', state)])
        #     if driver:
        #         for data in driver:
        #             lists.append(data.id) 
        #     spare = self.env['plan.trip.waybill'].sudo().search([('spare_id', '=', employee_id),
        #                                                       ('state', '=', state)])
        #     if spare:
        #         for data in spare:
        #             lists.append(data.id)  
        #     return lists

        lists = []
        if employee_id and state:
            employee_id = int(employee_id)
            if state == 'running' or state == 'close' or state == 'expense_claim':
                driver = self.env['plan.trip.waybill'].sudo().search([('driver_id', '=', employee_id),
                                                                ('state', '=', state)])
                spare = self.env['plan.trip.waybill'].sudo().search([('spare_id', '=', employee_id),
                                                                ('state', '=', state)])
                branch_manager = self.env['plan.trip.waybill'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id),
                                                                ('state', '=', state)])
            else:
                driver = self.env['plan.trip.waybill'].sudo().search([('driver_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                spare = self.env['plan.trip.waybill'].sudo().search([('spare_id', '=', employee_id),
                                                                ('state', 'in', ('open', 'advance_request', 'advance_withdraw'))])
                branch_manager = self.env['plan.trip.waybill'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id),
                                                                    ('state', 'in', ('draft', 'submit', 'open', 'advance_request', 'advance_withdraw', 'decline'))])
            if driver:
                for data in driver:
                    lists.append(data.id) 
            if spare:
                for data in spare:
                    lists.append(data.id)  
            if branch_manager:
                for data in branch_manager:
                    lists.append(data.id)
            list_set = set(lists)
            unique_list = (list(list_set))
            return unique_list
    
    def add_consumption_day_trip(self, day_trip_id=None, consumed_liter=None, description=None, date=None):
        if day_trip_id:
            day_trip = self.env['day.plan.trip'].sudo().browse(day_trip_id)
#             consumption = self.env['trip.fuel.consumption'].sudo().search([('day_trip_id', '=', day_trip_id)], order='id desc', limit=1)
#             last_odometer = 0
#             if consumption:
#                 last_odometer = consumption.current_odometer
#             else:
#                 last_odometer = day_trip.odometer
#             current_odometer = day_trip.vehicle_id.get_device_odometer()
            date_subtract = now_date = None
            if date:
                now_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date_subtract = now_date - timedelta(hours=6, minutes=30)
            else:
                date_subtract = datetime.now()
            
            print("origin date : ", date)
            print("now date : ", now_date)
            print("subtract date : ", date_subtract)

            values = {
                'day_trip_id': day_trip_id,
#                 'current_odometer': current_odometer,
#                 'last_odometer': last_odometer,
                'consumed_liter': consumed_liter,
                'description': description,
                'date': date_subtract,
            }
            fuel_consumption_id = self.env['trip.fuel.consumption'].create(values)
            if fuel_consumption_id:
#                 last_consumption = self.env['compsuption.great.average'].sudo().search([('vehicle_id', '=', day_trip.vehicle_id.id)], order='id desc', limit=1)
#                 if last_consumption:
#                     consumption_last_odometer = last_consumption.odometer
#                 else:
#                     consumption_last_odometer = 0
#                 travel_odometer = current_odometer - consumption_last_odometer
                filling_vals = {
                    'vehicle_id': day_trip.vehicle_id.id,
                    'employee_id': day_trip.driver_id.id,
                    'source_doc': day_trip.code,
                    'consumption_liter': fuel_consumption_id.consumed_liter,
                    'modified_date': fuel_consumption_id.date.date() if fuel_consumption_id.date else fields.Date.today(),
                    'trip_consumption_line_id': fuel_consumption_id.id,
#                     'last_odometer': consumption_last_odometer,
#                     'odometer': current_odometer,
#                     'travel_odometer': travel_odometer,
                }         
                self.env['compsuption.great.average'].sudo().create(filling_vals)
                if day_trip.vehicle_id.fuel_tank:
                    fuel_tank = day_trip.vehicle_id.fuel_tank
                    total_amount = total_liter = price_unit = 0
                    for line in fuel_tank.fule_filling_history_ids:
                        total_amount += line.amount
                        total_liter += line.fuel_liter
                    if total_liter != 0:
                        price_unit = total_amount / total_liter
                    if fuel_consumption_id.consumed_liter > total_liter:
                        raise ValidationError(_('Consumption Liter is greater than Fuel Balance.'))
                    else:
                        fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
                            'filling_date': fuel_consumption_id.date.date() if fuel_consumption_id.date else fields.Date.today(),
                            'price_per_liter': price_unit,
                            'fuel_liter': -fuel_consumption_id.consumed_liter,
                            'source_doc': day_trip.code,
                            'trip_consumption_line_id': fuel_consumption_id.id,
                        })
                        fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
                    
            return day_trip_id

    def add_consumption_plan_trip_product(self, line_id=None, plan_trip_id=None, route_id=None, consumed_liter=None, description=None, date=None):
        if plan_trip_id and route_id:
            fuel_consumption_obj = self.env['trip.fuel.consumption']
            consumption_obj = self.env['compsuption.great.average']
            fuel_filling_obj = self.env['fuel.filling.history']
            date_subtract = now_date = None
            if date:
                now_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date_subtract = now_date - timedelta(hours=6, minutes=30)
            else:
                date_subtract = datetime.now()
            plan_trip = self.env['plan.trip.product'].sudo().browse(plan_trip_id)
#             consumption = self.env['trip.fuel.consumption'].sudo().search([('trip_product_id', '=', plan_trip_id)], order='id desc', limit=1)
#             last_odometer = 0
#             if consumption:
#                 last_odometer = consumption.current_odometer
#             else:
#                 last_odometer = plan_trip.last_odometer
#             current_odometer = plan_trip.vehicle_id.get_device_odometer()
            if line_id:
                existing_line = fuel_consumption_obj.sudo().search([('id', '=', line_id)])
                if existing_line:
                    liter = existing_line.consumed_liter + consumed_liter
                    if plan_trip.vehicle_id.fuel_tank:
                        fuel_tank = plan_trip.vehicle_id.fuel_tank
                        total_amount = total_liter = price_unit = 0
                        for line in fuel_tank.fule_filling_history_ids:
                            total_amount += line.amount
                            total_liter += line.fuel_liter
                        if total_liter != 0:
                            price_unit = total_amount / total_liter
                        if liter > total_liter:
                            raise ValidationError(_('Consumption Liter is greater than Fuel Balance.'))
                        else:
                            existing_line.write({
                                'consumed_liter': liter,
                                'description': description,
                                'date': date_subtract,
        #                         'current_odometer': current_odometer,
        #                         'last_odometer': last_odometer,
                            })
                            ext_fuel_consumption = consumption_obj.sudo().search([('source_doc', '=', plan_trip.code), ('trip_consumption_line_id', '=', line_id)])
                            ext_fuel_filling = fuel_filling_obj.sudo().search([('source_doc', '=', plan_trip.code), ('trip_consumption_line_id', '=', line_id)])
                            if ext_fuel_consumption:
                                if ext_fuel_consumption.consumption_liter != liter:
                                    ext_fuel_consumption.consumption_liter = liter
                            else:
                                consumption_obj.sudo().create({
                                    'vehicle_id': plan_trip.vehicle_id.id,
                                    'employee_id': plan_trip.driver_id.id,
                                    'source_doc': plan_trip.code,
                                    'consumption_liter': liter,
                                    'modified_date': existing_line.date.date() if existing_line.date else fields.Date.today(),
                                    'trip_consumption_line_id': line_id,
                                })
                            if ext_fuel_filling:
                                if ext_fuel_filling.fuel_liter != liter:
                                    ext_fuel_filling.fuel_liter = liter * (-1)
                            else:
                                fuel_filling_id = fuel_filling_obj.sudo().create({
                                    'filling_date': existing_line.date.date() if existing_line.date else fields.Date.today(),
                                    'price_per_liter': price_unit,
                                    'fuel_liter': -liter,
                                    'source_doc': plan_trip.code,
                                    'trip_consumption_line_id': line_id,
                                })
                                fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
            else:
                values = {
                    'trip_product_id': plan_trip_id,
                    'route_id': route_id,
#                     'current_odometer': current_odometer,
#                     'last_odometer': last_odometer,
                    'consumed_liter': consumed_liter,
                    'description': description,
                    'date': date_subtract,
                }
                fuel_consumption_id = fuel_consumption_obj.sudo().create(values)
                if fuel_consumption_id:
#                     last_consumption = self.env['compsuption.great.average'].sudo().search([('vehicle_id', '=', plan_trip.vehicle_id.id)], order='id desc', limit=1)
#                     if last_consumption:
#                         consumption_last_odometer = last_consumption.odometer
#                     else:
#                         consumption_last_odometer = 0
#                     travel_odometer = current_odometer - consumption_last_odometer
                    filling_vals = {
                        'vehicle_id': plan_trip.vehicle_id.id,
                        'employee_id': plan_trip.driver_id.id,
                        'source_doc': plan_trip.code,
                        'consumption_liter': fuel_consumption_id.consumed_liter,
                        'modified_date': fuel_consumption_id.date.date() if fuel_consumption_id.date else fields.Date.today(),
                        'trip_consumption_line_id': fuel_consumption_id.id,
#                         'last_odometer': consumption_last_odometer,
#                         'odometer': current_odometer,
#                         'travel_odometer': travel_odometer,
                    }         
                    consumption_obj.sudo().create(filling_vals)
                    if plan_trip.vehicle_id.fuel_tank:
                        fuel_tank = plan_trip.vehicle_id.fuel_tank
                        total_amount = total_liter = price_unit = 0
                        for line in fuel_tank.fule_filling_history_ids:
                            total_amount += line.amount
                            total_liter += line.fuel_liter
                        if total_liter != 0:
                            price_unit = total_amount / total_liter
                        if fuel_consumption_id.consumed_liter > total_liter:
                            raise ValidationError(_('Consumption Liter is greater than Fuel Balance.'))
                        else:
                            fuel_filling_id = fuel_filling_obj.sudo().create({
                                'filling_date': fuel_consumption_id.date.date() if fuel_consumption_id.date else fields.Date.today(),
                                'price_per_liter': price_unit,
                                'fuel_liter': -fuel_consumption_id.consumed_liter,
                                'source_doc': plan_trip.code,
                                'trip_consumption_line_id': fuel_consumption_id.id,
                            })
                            fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})

            return plan_trip_id

    def add_consumption_plan_trip_waybill(self, line_id=None, plan_trip_id=None, route_id=None, consumed_liter=None, description=None, date=None):
        if plan_trip_id and route_id:
            fuel_consumption_obj = self.env['trip.fuel.consumption']
            consumption_obj = self.env['compsuption.great.average']
            fuel_filling_obj = self.env['fuel.filling.history']
            date_subtract = now_date = None
            if date:
                now_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date_subtract = now_date - timedelta(hours=6, minutes=30)
            else:
                date_subtract = datetime.now()
            plan_trip = self.env['plan.trip.waybill'].sudo().browse(plan_trip_id)
#             consumption = self.env['trip.fuel.consumption'].sudo().search([('trip_waybill_id', '=', plan_trip_id)], order='id desc', limit=1)
#             last_odometer = 0
#             if consumption:
#                 last_odometer = consumption.current_odometer
#             else:
#                 last_odometer = plan_trip.last_odometer
#             current_odometer = plan_trip.vehicle_id.get_device_odometer()
            if line_id:
                existing_line = fuel_consumption_obj.sudo().search([('id', '=', line_id)])
                if existing_line:
                    liter = existing_line.consumed_liter + consumed_liter
                    if plan_trip.vehicle_id.fuel_tank:
                        fuel_tank = plan_trip.vehicle_id.fuel_tank
                        total_amount = total_liter = price_unit = 0
                        for line in fuel_tank.fule_filling_history_ids:
                            total_amount += line.amount
                            total_liter += line.fuel_liter
                        if total_liter != 0:
                            price_unit = total_amount / total_liter
                        if liter > total_liter:
                            raise ValidationError(_('Consumption Liter is greater than Fuel Balance.'))
                        else:
                            existing_line.write({
                                'consumed_liter': liter,
                                'description': description,
                                'date': date_subtract,
        #                         'current_odometer': current_odometer,
        #                         'last_odometer': last_odometer,
                            })
                            ext_fuel_consumption = consumption_obj.sudo().search([('source_doc', '=', plan_trip.code), ('trip_consumption_line_id', '=', line_id)])
                            ext_fuel_filling = fuel_filling_obj.sudo().search([('source_doc', '=', plan_trip.code), ('trip_consumption_line_id', '=', line_id)])
                            if ext_fuel_consumption:
                                if ext_fuel_consumption.consumption_liter != liter:
                                    ext_fuel_consumption.consumption_liter = liter
                            else:
                                consumption_obj.sudo().create({
                                    'vehicle_id': plan_trip.vehicle_id.id,
                                    'employee_id': plan_trip.driver_id.id,
                                    'source_doc': plan_trip.code,
                                    'consumption_liter': liter,
                                    'modified_date': existing_line.date.date() if existing_line.date else fields.Date.today(),
                                    'trip_consumption_line_id': line_id,
                                })
                            if ext_fuel_filling:
                                if ext_fuel_filling.fuel_liter != liter:
                                    ext_fuel_filling.fuel_liter = liter * (-1)
                            else:
                                fuel_filling_id = fuel_filling_obj.sudo().create({
                                    'filling_date': existing_line.date.date() if existing_line.date else fields.Date.today(),
                                    'price_per_liter': price_unit,
                                    'fuel_liter': -liter,
                                    'source_doc': plan_trip.code,
                                    'trip_consumption_line_id': line_id,
                                })
                                fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
            else:
                values = {
                    'trip_waybill_id': plan_trip_id,
                    'route_id': route_id,
#                     'current_odometer': current_odometer,
#                     'last_odometer': last_odometer,
                    'consumed_liter': consumed_liter,
                    'description': description,
                    'date': date_subtract,
                }
                fuel_consumption_id = fuel_consumption_obj.sudo().create(values)
                if fuel_consumption_id:
#                     last_consumption = self.env['compsuption.great.average'].sudo().search([('vehicle_id', '=', plan_trip.vehicle_id.id)], order='id desc', limit=1)
#                     if last_consumption:
#                         consumption_last_odometer = last_consumption.odometer
#                     else:
#                         consumption_last_odometer = 0
#                     travel_odometer = current_odometer - consumption_last_odometer
                    filling_vals = {
                        'vehicle_id': plan_trip.vehicle_id.id,
                        'employee_id': plan_trip.driver_id.id,
                        'source_doc': plan_trip.code,
                        'consumption_liter': fuel_consumption_id.consumed_liter,
                        'modified_date': fuel_consumption_id.date.date() if fuel_consumption_id.date else fields.Date.today(),
                        'trip_consumption_line_id': fuel_consumption_id.id,
#                         'last_odometer': consumption_last_odometer,
#                         'odometer': current_odometer,
#                         'travel_odometer': travel_odometer,
                    }         
                    consumption_obj.sudo().create(filling_vals)
                    if plan_trip.vehicle_id.fuel_tank:
                        fuel_tank = plan_trip.vehicle_id.fuel_tank
                        total_amount = total_liter = price_unit = 0
                        for line in fuel_tank.fule_filling_history_ids:
                            total_amount += line.amount
                            total_liter += line.fuel_liter
                        if total_liter != 0:
                            price_unit = total_amount / total_liter
                        if fuel_consumption_id.consumed_liter > total_liter:
                            raise ValidationError(_('Consumption Liter is greater than Fuel Balance.'))
                        else:
                            fuel_filling_id = fuel_filling_obj.sudo().create({
                                'filling_date': fuel_consumption_id.date.date() if fuel_consumption_id.date else fields.Date.today(),
                                'price_per_liter': price_unit,
                                'fuel_liter': -fuel_consumption_id.consumed_liter,
                                'source_doc': plan_trip.code,
                                'trip_consumption_line_id': fuel_consumption_id.id,
                            })
                            fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
              
            return plan_trip_id

    def end_day_trip(self, day_trip_id=None, consumed_liter=None, description=None, vehicle_id=None, 
                        employee_id=None, source_doc=None, filling_date=None, filling_liter=None, 
                        amount=None, odometer=None, prev_odometer=None, slip_no=None, shop=None):
        
        if day_trip_id:
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id) 
            values = {
                'day_trip_id': day_trip_id,
                'consumed_liter': consumed_liter,
                'description': description,
            }
            fuel_consumption_id = self.env['trip.fuel.consumption'].create(values)      

            self.env['fleet.vehicle.log.fuel'].create({
                'vehicle_id': vehicle_id,
                'employee_id': vehicle.incharge_id.id,
                'fuel_tank_id': vehicle.fuel_tank.id,
                'liter': filling_liter,
                # 'amount': amount,
                # 'odometer': odometer,
                # 'previous_odometer': prev_odometer,
                # 'prev_odo': prev_odometer,
                'date': filling_date if filling_date else fields.Date.today(),
                'source_doc': source_doc,
                # 'inv_ref': slip_no,
                # 'shop': shop
            })
            filling_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': employee_id,
                'source_doc': source_doc,
                'consumption_liter': filling_liter,
                'modified_date': filling_date if filling_date else fields.Date.today(),
            }         
            self.env['compsuption.great.average'].create(filling_vals)
            if vehicle.fuel_tank:
                fuel_filling_id = self.env['fuel.filling.history'].create({
                    'filling_date': filling_date if filling_date else fields.Date.today(),
                    # 'price_per_liter': amount,
                    'fuel_liter': filling_liter,
                    'source_doc': source_doc,
                })
                vehicle.fuel_tank.write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
                if consumed_liter:
                    liter = consumed_liter * (-1)
                    fuel_consumed_id = self.env['fuel.filling.history'].create({
                        'filling_date': filling_date if filling_date else fields.Date.today(),
                        # 'price_per_liter': amount,
                        'fuel_liter': liter,
                        'source_doc': source_doc,
                    })
                    vehicle.fuel_tank.write({'fule_filling_history_ids': [(4, fuel_consumed_id.id)]})
            
            return day_trip_id
        
    def end_plan_trip_product(self, plan_trip_id=None, route_id=None, consumed_liter=None, description=None, 
                                vehicle_id=None, employee_id=None, source_doc=None, filling_date=None, filling_liter=None,
                                amount=None, odometer=None, prev_odometer=None, slip_no=None, shop=None):
        
        if plan_trip_id and route_id:
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
            consumption = self.env['trip.fuel.consumption'].sudo().search([('trip_product_id', '=', plan_trip_id),
                                                                           ('route_id', '=', route_id)])
            if consumption:                
                vals = {
                        'consumed_liter': consumed_liter,
                        'description': description,
                    }
                consumption.write(vals)           
            
            self.env['fleet.vehicle.log.fuel'].create({
                'vehicle_id': vehicle_id,
                'employee_id': vehicle.incharge_id.id,
                'fuel_tank_id': vehicle.fuel_tank.id,
                'liter': filling_liter,
                # 'amount': amount,
                # 'odometer': odometer,
                # 'previous_odometer': prev_odometer,
                # 'prev_odo': prev_odometer,
                'date': filling_date if filling_date else fields.Date.today(),
                'source_doc': source_doc,
                # 'inv_ref': slip_no,
                # 'shop': shop
            })

            filling_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': employee_id,
                'source_doc': source_doc,
                'consumption_liter': filling_liter,
                'modified_date': filling_date if filling_date else fields.Date.today(),
            }         
            self.env['compsuption.great.average'].create(filling_vals)   
            if vehicle.fuel_tank:
                fuel_filling_id = self.env['fuel.filling.history'].create({
                    'filling_date': filling_date if filling_date else fields.Date.today(),
                    # 'price_per_liter': amount,
                    'fuel_liter': filling_liter,
                    'source_doc': source_doc,
                })
                vehicle.fuel_tank.write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
                if consumed_liter:
                    liter = consumed_liter * (-1)
                    fuel_consumed_id = self.env['fuel.filling.history'].create({
                        'filling_date': filling_date if filling_date else fields.Date.today(),
                        # 'price_per_liter': amount,
                        'fuel_liter': liter,
                        'source_doc': source_doc,
                    })
                    vehicle.fuel_tank.write({'fule_filling_history_ids': [(4, fuel_consumed_id.id)]})       
            return plan_trip_id
            
    def end_plan_trip_waybill(self, plan_trip_id=None, route_id=None, consumed_liter=None, description=None, 
                                vehicle_id=None, employee_id=None, source_doc=None, filling_date=None, filling_liter=None,
                                amount=None, odometer=None, prev_odometer=None, slip_no=None, shop=None):
        
        if plan_trip_id and route_id:
            vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
            consumption = self.env['trip.fuel.consumption'].sudo().search([('trip_waybill_id', '=', plan_trip_id),
                                                                           ('route_id', '=', route_id)])
            if consumption:                
                vals = {
                        'consumed_liter': consumed_liter,
                        'description': description,
                    }
                consumption.write(vals)   

            self.env['fleet.vehicle.log.fuel'].create({
                'vehicle_id': vehicle_id,
                'employee_id': vehicle.incharge_id.id,
                'fuel_tank_id': vehicle.fuel_tank.id,
                'liter': filling_liter,
                # 'amount': amount,
                # 'odometer': odometer,
                # 'previous_odometer': prev_odometer,
                # 'prev_odo': prev_odometer,
                'date': filling_date if filling_date else fields.Date.today(),
                'source_doc': source_doc,
                # 'inv_ref': slip_no,
                # 'shop': shop
            })

            filling_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': employee_id,
                'source_doc': source_doc,
                'consumption_liter': filling_liter,
                'modified_date': filling_date if filling_date else fields.Date.today(),
            }         
            self.env['compsuption.great.average'].create(filling_vals)    
            if vehicle.fuel_tank:
                fuel_filling_id = self.env['fuel.filling.history'].create({
                    'filling_date': filling_date if filling_date else fields.Date.today(),
                    # 'price_per_liter': amount,
                    'fuel_liter': filling_liter,
                    'source_doc': source_doc,
                })
                vehicle.fuel_tank.write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
                if consumed_liter:
                    liter = consumed_liter * (-1)
                    fuel_consumed_id = self.env['fuel.filling.history'].create({
                        'filling_date': filling_date if filling_date else fields.Date.today(),
                        # 'price_per_liter': amount,
                        'fuel_liter': liter,
                        'source_doc': source_doc,
                    })
                    vehicle.fuel_tank.write({'fule_filling_history_ids': [(4, fuel_consumed_id.id)]})      
            return plan_trip_id                  
    
    def get_pms_approval_lists(self, employee_id=None):
        lists = []
        if employee_id:
            employee_id = int(employee_id) 
            period = self.get_pms_period()
            employees = self.env['hr.employee'].sudo().search([('approve_manager', '=', employee_id)])
            if employees:
                pms = self.env['employee.performance'].sudo().search([('employee_id', 'in', employees.ids),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end),
                                                                      ('state', 'in', ('mid_year_self_assessment', 'year_end_self_assessment'))])
                if pms:
                    for data in pms:
                        lists.append(data.id) 

            employees1 = self.env['hr.employee'].sudo().search([('dotted_line_manager_id', '=', employee_id)])
            if employees1:
                pms = self.env['employee.performance'].sudo().search([('employee_id', 'in', employees1.ids),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end),
                                                                      ('state', 'in', ('mid_year_manager_approve', 'year_end_manager_approve'))])
                if pms:
                    for data in pms:
                        lists.append(data.id) 

            employees2 = self.env['hr.employee'].sudo().search([('branch_id.hr_manager_id', '=', employee_id)])
            if employees2:
                pms = self.env['employee.performance'].sudo().search([('employee_id', 'in', employees2.ids),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end),
                                                                      ('state', 'in', ('mid_year_dotted_manager_approve', 'year_end_dotted_manager_approve'))])
                if pms:
                    for data in pms:
                        lists.append(data.id) 
        return lists
        
    def get_pms_approve_lists(self, employee_id=None):
        lists = []
        if employee_id:
            employee_id = int(employee_id) 
            period = self.get_pms_period()
            employees = self.env['hr.employee'].sudo().search([('approve_manager', '=', employee_id)])
            if employees:
                pms = self.env['employee.performance'].sudo().search([('employee_id', 'in', employees.ids),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end),
                                                                      ('state', 'in', ('mid_year_manager_approve', 'mid_year_dotted_manager_approve', 'mid_year_hr_approve', 'year_end_manager_approve', 'year_end_dotted_manager_approve', 'sent_to_manager', 'year_end_hr_approve'))])
                if pms:
                    for data in pms:
                        lists.append(data.id) 

            employees1 = self.env['hr.employee'].sudo().search([('dotted_line_manager_id', '=', employee_id)])
            if employees1:
                pms = self.env['employee.performance'].sudo().search([('employee_id', 'in', employees1.ids),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end),
                                                                      ('state', 'in', ('mid_year_dotted_manager_approve', 'mid_year_hr_approve', 'year_end_self_assessment', 'year_end_dotted_manager_approve', 'sent_to_manager', 'year_end_hr_approve'))])
                if pms:
                    for data in pms:
                        lists.append(data.id) 

            #employees2 = self.env['hr.employee'].sudo().search([('branch_id.hr_manager_id', '=', employee_id)])
            employees2 = self.env['hr.employee'].sudo().search(
                            [('approve_manager', '=', employee_id)])
            if employees2:
                pms = self.env['employee.performance'].sudo().search([('employee_id', 'in', employees2.ids),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end),
                                                                      ('state', 'in', ('mid_year_hr_approve', 'year_end_self_assessment', 'year_end_manager_approve', 'sent_to_manager', 'year_end_hr_approve'))])
                if pms:
                    for data in pms:
                        lists.append(data.id) 
        return lists
    
    def update_missed_in_out_attendances(self,attendance_id):
        if attendance_id:
            attendance_obj = self.env['hr.attendance'].browse(attendance_id)
            if attendance_obj.is_absent is True:
                attendance_obj.write({
                    'is_absent': False,
                    'state': 'approve'
                })
                return True
            
            local = self._context.get('tz', 'Asia/Yangon') or 'Asia/Yangon'
            local_tz = timezone(local)
            print(fields.Datetime.now())
            current = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz)
            print(current)
            self.env.cr.execute("""select (
            select %s::timestamp without time zone + interval '5 hours 30 minutes')::date as raw_date""",(attendance_obj.check_in,))
            result = self.env.cr.dictfetchall()[0]
            
            #yesterday = attendance_obj.check_in.date()
            yesterday = result['raw_date']
            print(yesterday)
            dayofweek = yesterday.weekday()
            print(dayofweek)
            for emp in self.env['hr.attendance'].browse(attendance_id):
            #for emp in self.env['hr.employee'].search([('id', '=', 6158)]):
                holiday = self.env['public.holidays.line'].search([('date','=',yesterday)],limit=1)
                if emp.missed == False and emp.early_out_minutes == 0 and emp.late_minutes == 0 and emp.check_out:
                    emp.write({'state': 'approve','missed':False})
                    continue
                
                if emp.check_in and emp.check_out and (emp.early_out_minutes != 0 or emp.late_minutes != 0):
                    t_checkin = emp.check_in - timedelta(hours = emp.late_minutes) 
                    t_checkout = emp.check_out + timedelta(hours = emp.early_out_minutes)
                    
                    emp.write({'check_in':t_checkin,'check_out':t_checkout,'state': 'approve','missed':False})
                    continue
#                 if emp.check_out and emp.early_out_minutes == 0 and emp.late_minutes == 0:
#                     emp.write({'missed':False})
#                     continue
                
                tz = timezone(emp.employee_id.tz or emp.employee_id.resource_calendar_id.tz)
                local_dt = emp.check_in.astimezone(tz)
                dt_float = time_to_float(local_dt)
                    
                if emp.employee_id.resource_calendar_id:
                    tz = timezone(emp.employee_id.resource_calendar_id.tz or 'Asia/Yangon')
                    date_start = tz.localize(fields.Datetime.to_datetime(yesterday), is_dst=True).astimezone(tz=UTC)
                    date_stop = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), datetime.max.time()), is_dst=True).astimezone(tz=UTC)
                    print(date_start)
                    print(date_stop)
                    domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', emp.employee_id.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                    if emp.employee_id.resource_calendar_id.two_weeks_calendar:
                        week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                        domain += [('week_type', '=', str(week_type))]
    
                    working_hours = self.env['resource.calendar.attendance'].search(domain)
                    if working_hours:
                        attendances = self.env['hr.attendance'].search([('id', '=', emp.id)
                                                                        #('check_in', '>=', date_start),
                                                                        #('check_in', '<', date_stop)
                                                                        ])
                        if len(working_hours) == 1:
                            for wh in working_hours:
                                first_time = True
                                check_in = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_from)), is_dst=True).astimezone(tz=UTC)
                                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                t_check_out = fields.Datetime.to_datetime(check_in.strftime(DT))
                                   
                                if t_check_out < emp.check_in:
                                    emp.write({'missed':False,'check_in':check_in.strftime(DT),'check_out':emp.check_in,'state': 'approve'})
                                else:
                                    emp.write({'missed':False,'check_out':check_out.strftime(DT),'state': 'approve'})
                                     
                                #if emp.chech_in > check_in:
                                
                        elif len(working_hours) > len(emp):
                            distinct = morn_start = morn_end = night_start = night_end = dist_start = dist_end = False
                            morning = working_hours.filtered(lambda h: round(h.hour_from) == 0)
                            night = working_hours.filtered(lambda h: round(h.hour_to) == 24)
                            distincts = working_hours.filtered(lambda h: round(h.hour_from) != 0 and round(h.hour_to) != 24)
                            if len(distincts) == 1:
                                distinct = distincts
                            if morning:
                                morn_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_from)), is_dst=True).astimezone(tz=UTC)
                                morn_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(morning.hour_to)), is_dst=True).astimezone(tz=UTC)
                                t_morn_start = fields.Datetime.to_datetime(morn_start.strftime(DT))
                                t_morn_end = fields.Datetime.to_datetime(morn_end.strftime(DT))
                                
                            if night:
                                night_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_from)), is_dst=True).astimezone(tz=UTC)
                                night_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(night.hour_to)), is_dst=True).astimezone(tz=UTC)
                                t_night_start = fields.Datetime.to_datetime(night_start.strftime(DT))
                                t_night_end = fields.Datetime.to_datetime(night_end.strftime(DT))
                            if distinct:
                                dist_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_from)), is_dst=True).astimezone(tz=UTC)
                                dist_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(distinct.hour_to)), is_dst=True).astimezone(tz=UTC)
                                t_dist_start = fields.Datetime.to_datetime(dist_start.strftime(DT))
                                t_dist_end = fields.Datetime.to_datetime(dist_end.strftime(DT))
                            if morning and night:
                                if t_morn_start < emp.check_in <= t_morn_end:                                
                                    emp.write({'check_out':night_end.strftime(DT),'missed':False,'state': 'approve'})
                                elif t_night_start < emp.check_in <= t_night_end:
                                    emp.write({'check_out':morn_end.strftime(DT),'missed':False,'state': 'approve'})
                            elif morning and distinct:
                                
                                if t_morn_start < emp.check_in <= t_morn_end:
                                    emp.write({'check_out':dist_end.strftime(DT),'missed':False,'state': 'approve'})
                                else:
                                    emp.write({'check_out':morn_end.strftime(DT),'missed':False,'state': 'approve'})
                                    #attendance_id = self.create({'employee_id': emp.employee_id.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
                                    
                            elif distinct and night:
                                if t_night_start < emp.check_in <= t_night_end:                                
                                    emp.write({'check_out':dist_end.strftime(DT),'missed':False,'state': 'approve'})
                                    #attendance_id = self.create({'employee_id': emp.employee_id.id, 'check_in': night_start.strftime(DT), 'check_out': night_end.strftime(DT), 'is_absent': True})
                                   
                                else:
                                    emp.write({'check_out':night_end.strftime(DT),'missed':False,'state': 'approve'})
                                    #attendance_id = self.create({'employee_id': emp.employee_id.id, 'check_in': dist_start.strftime(DT), 'check_out': dist_end.strftime(DT), 'is_absent': True})
#                                     self.check_leave_or_travel(attendance_id)
#                                     self.check_trip(attendance_id)
                            else:
                                for dist in distincts:
                                    hr_start = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_from)), is_dst=True).astimezone(tz=UTC)
                                    hr_end = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(dist.hour_to)), is_dst=True).astimezone(tz=UTC)
                                    emp.write({'check_out':hr_end.strftime(DT),'missed':False,'state': 'approve'})
                                    #attendance_id = self.create({'employee_id': emp.employee_id.id, 'check_in': hr_start.strftime(DT), 'check_out': hr_end.strftime(DT), 'is_absent': True})
                                    
                                    
    def action_on_duty(self, attendance_id=None):
        if attendance_id:
            attendance_obj = self.env['hr.attendance'].browse(attendance_id)
            if attendance_obj.is_absent is True:
                attendance_obj.write({
                    'is_absent': False,
                    'state': 'approve'
                })
                return True
            if attendance_obj.missed is True:
                resrc_calendar = attendance_obj.employee_id.resource_calendar_id
                check_in = attendance_obj.check_in
                check_out = attendance_obj.check_out
                day = date = start_time = end_time = ''
                if check_in:
                    day = str(check_in.weekday())
                    date = str(check_in.date())
                if check_out:
                    day = str(check_out.weekday())
                    date = str(check_out.date())
                attendance_obj.write({
                    'missed': False,
                    'state': 'approve'
                })
                if resrc_calendar.no_attendance == False and resrc_calendar.holiday == False and resrc_calendar.one_day_off == False and resrc_calendar.no_holidays == False:
                    for line in resrc_calendar.attendance_ids:
                        if line.dayofweek == day:
                            start_time = str(datetime.timedelta(hours=line.hour_from))
                            end_time = str(datetime.timedelta(hours=line.hour_to))
                            break
                
                if not check_in:
                    date += ' ' + start_time
                    attendance_obj.write({
                        'check_in': date
                    })
                if not check_out:
                    date += ' ' + start_time
                    attendance_obj.write({
                        'check_out': date
                    })
                return True
            
            else:
                return False
            
    def get_travel_expense_attachment(self, line_id=None):
        
        if line_id:
            expense_line_obj = self.env['hr.travel.expense.line'].browse(line_id)
            if expense_line_obj:
                return expense_line_obj.attached_file        
    
    def get_maintenance_request(self, employee_id=None, state=None):
        lists = []
        if employee_id and state:
            employee_id = int(employee_id)    
            if state == 'planned':   
                branch_manager_corrective = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('submit', 'approved'))])
                if branch_manager_corrective:
                    for data in branch_manager_corrective:
                        lists.append(data.id)
                branch_manager_preventive = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'in', ('propose', 'submit', 'approved'))])
                if branch_manager_preventive:
                    for data in branch_manager_preventive:
                        lists.append(data.id)
                
                driver_corrective = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('propose', 'submit', 'approved'))])
                if driver_corrective:
                    for data in driver_corrective:
                        lists.append(data.id)
                driver_preventive = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', '=', 'approved')])
                if driver_preventive:
                    for data in driver_preventive:
                        lists.append(data.id)
                
                spare_corrective = self.env['maintenance.request'].sudo().search(['|', ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('propose', 'submit', 'approved'))])
                if spare_corrective:
                    for data in spare_corrective:
                        lists.append(data.id)
                spare_preventive = self.env['maintenance.request'].sudo().search(['|', ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', '=', 'approved')])
                if spare_preventive:
                    for data in spare_preventive:
                        lists.append(data.id)
               
                incharge_corrective = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', '=', 'approved')])
                if incharge_corrective:
                    for data in incharge_corrective:
                        lists.append(data.id)
                incharge_preventive = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'in', ('propose', 'approved'))])
                if incharge_preventive:
                    for data in incharge_preventive:
                        lists.append(data.id)
               
            if state == 'maintenance':
                branch_manager_corrective = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('start', 'reproposed', 'resubmitted', 'approve'))])
                if branch_manager_corrective:
                    for data in branch_manager_corrective:
                        lists.append(data.id)
                branch_manager_preventive = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'in', ('start', 'reproposed', 'resubmitted', 'approve'))])
                if branch_manager_preventive:
                    for data in branch_manager_preventive:
                        lists.append(data.id)
                
                driver_corrective = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('start', 'reproposed', 'resubmitted', 'approve'))])
                if driver_corrective:
                    for data in driver_corrective:
                        lists.append(data.id)
                driver_preventive = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'in', ('start', 'reproposed', 'resubmitted', 'approve'))])
                if driver_preventive:
                    for data in driver_preventive:
                        lists.append(data.id)
                
                spare_corrective = self.env['maintenance.request'].sudo().search(['|', ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('start', 'reproposed', 'resubmitted', 'approve'))])
                if spare_corrective:
                    for data in spare_corrective:
                        lists.append(data.id)
                spare_preventive = self.env['maintenance.request'].sudo().search(['|', ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'in', ('start', 'reproposed', 'resubmitted', 'approve'))])
                if spare_preventive:
                    for data in spare_preventive:
                        lists.append(data.id)
               
                incharge_corrective = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'in', ('start', 'reproposed', 'approve'))])
                if incharge_corrective:
                    for data in incharge_corrective:
                        lists.append(data.id)
                incharge_preventive = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'in', ('start', 'reproposed', 'approve'))])
                if incharge_preventive:
                    for data in incharge_preventive:
                        lists.append(data.id)
                
            if state == 'done':
                branch_manager = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('state', 'in', ('qc', 'done'))])
                if branch_manager:
                    for data in branch_manager:
                        lists.append(data.id)
                
                driver = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('state', 'in', ('qc', 'done'))])
                if driver:
                    for data in driver:
                        lists.append(data.id)
                
                spare = self.env['maintenance.request'].sudo().search(['|', ('spare1_id', '=', employee_id), ('spare2_id', '=', employee_id), ('state', 'in', ('qc', 'done'))])
                if spare:
                    for data in spare:
                        lists.append(data.id)
                
                incharge = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('state', 'in', ('qc', 'done'))])
                if incharge:
                    for data in incharge:
                        lists.append(data.id)

            list_set = set(lists)
            unique_list = (list(list_set))
            return unique_list

    # def get_maintenance_request(self, employee_id=None):
    #     lists = []
    #     if employee_id:    
    #         branch_manager_corrective = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'not in', ('propose', 'draft'))])
    #         if branch_manager_corrective:
    #             for data in branch_manager_corrective:
    #                 lists.append(data.id)
    #         branch_manager_preventive = self.env['maintenance.request'].sudo().search([('driver_id.branch_id.manager_id', '=', employee_id), ('maintenance_type', '=', 'preventive')])
    #         if branch_manager_preventive:
    #             for data in branch_manager_preventive:
    #                 lists.append(data.id)

    #         driver_corrective = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'not in', ('submit', 'resubmitted'))])
    #         if driver_corrective:
    #             for data in driver_corrective:
    #                 lists.append(data.id)
    #         driver_preventive = self.env['maintenance.request'].sudo().search([('driver_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'not in', ('propose', 'submit', 'resubmitted'))])
    #         if driver_preventive:
    #             for data in driver_preventive:
    #                 lists.append(data.id)

    #         incharge_corrective = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('maintenance_type', '=', 'corrective'), ('state', 'not in', ('propose', 'submit', 'resubmitted'))])
    #         if incharge_corrective:
    #             for data in incharge_corrective:
    #                 lists.append(data.id)
    #         incharge_preventive = self.env['maintenance.request'].sudo().search([('vehicle_id.incharge_id', '=', employee_id), ('maintenance_type', '=', 'preventive'), ('state', 'not in', ('submit', 'resubmitted'))])
    #         if incharge_preventive:
    #             for data in incharge_preventive:
    #                 lists.append(data.id)

    #         list_set = set(lists)
    #         unique_list = (list(list_set))
    #         return unique_list

    def add_pocket_expense_lines(self, parent_id=None, pocket_lines=None):
        if parent_id and pocket_lines:
            expense_id = self.env['hr.pocket.expense'].sudo().browse(parent_id)
#             old_lines = self.env['hr.pocket.expense.line'].sudo().search([('line_id', '=', parent_id)])
#             old_fuel_logs = self.env['fleet.vehicle.log.fuel'].sudo().search([('source_doc', '=', expense_id.number)])
#             old_fuel_costs = self.env['fleet.vehicle.cost'].sudo().search([('vendor_bill_ref', '=', expense_id.number)])
#             old_fuel_consumptions = self.env['compsuption.great.average'].sudo().search([('source_doc', '=', expense_id.number)])
#             old_fuel_filling_lines = self.env['fuel.filling.history'].sudo().search([('source_doc', '=', expense_id.number)])
#             if old_lines:
#                 old_lines.unlink()
#             if old_fuel_logs:
#                 old_fuel_logs.unlink()
#             if old_fuel_costs:
#                 old_fuel_costs.unlink()
#             if old_fuel_consumptions:
#                 old_fuel_consumptions.unlink()
#             if old_fuel_filling_lines:
#                 old_fuel_filling_lines.unlink()
            for line in pocket_lines:
                if line['id'] == 0:
                    expense_id.write({'pocket_line': [(0, None, {
                        'line_id': parent_id,
                        'date': line['date'],
                        'categ_id': line['categ_id'],
                        'product_id': line['product_id'],
                        'description': line['description'],
                        'vehicle_id': line['vehicle_id'],
                        'qty': line['qty'],
                        'price_unit': line['price_unit'],
                        'price_subtotal': line['price_subtotal'],
                        'attached_file': line['attached_file'], 
                        'attachment_include': line['attachment_include'],
                    })]})
                
                    if line['vehicle_id']:
                        vehicle_id = line['vehicle_id']
                        date = line['date']
                        qty = line['qty']
                        description = line['description']
                        price_unit = line['price_unit']
                        amount = line['price_subtotal']
                        self.create_vehicle_cost_when_update(vehicle_id, expense_id, date, qty, description, price_unit, amount)
            return parent_id
    
    def add_travel_expense_lines(self, parent_id=None, travel_lines=None):
        if parent_id and travel_lines:
            expense_id = self.env['hr.travel.expense'].sudo().browse(parent_id)
#             old_lines = self.env['hr.travel.expense.line'].sudo().search([('line_id', '=', parent_id)])
#             old_fuel_logs = self.env['fleet.vehicle.log.fuel'].sudo().search([('source_doc', '=', expense_id.number)])
#             old_fuel_costs = self.env['fleet.vehicle.cost'].sudo().search([('vendor_bill_ref', '=', expense_id.number)])
#             old_fuel_consumptions = self.env['compsuption.great.average'].sudo().search([('source_doc', '=', expense_id.number)])
#             old_fuel_filling_lines = self.env['fuel.filling.history'].sudo().search([('source_doc', '=', expense_id.number)])
#             if old_lines:
#                 old_lines.unlink()
#             if old_fuel_logs:
#                 old_fuel_logs.unlink()
#             if old_fuel_costs:
#                 old_fuel_costs.unlink()
#             if old_fuel_consumptions:
#                 old_fuel_consumptions.unlink()
#             if old_fuel_filling_lines:
#                 old_fuel_filling_lines.unlink()
            for line in travel_lines:
                if line['id'] == 0:
                    expense_id.write({'travel_line': [(0, None, {
                        'line_id': parent_id,
                        'date': line['date'],
                        'categ_id': line['categ_id'],
                        'product_id': line['product_id'],
                        'description': line['description'],
                        'vehicle_id': line['vehicle_id'],
                        'qty': line['qty'],
                        'price_unit': line['price_unit'],
                        'price_subtotal': line['price_subtotal'],
                        'attached_file': line['attached_file'],
                        'attached_filename': line['attached_filename'],
                        'image1': line['image1'],
                        'image1_filename': line['image1_filename'],
                        'image2': line['image2'],
                        'image2_filename': line['image2_filename'],
                        'image3': line['image3'],
                        'image3_filename': line['image3_filename'],
                        'image4': line['image4'],
                        'image4_filename': line['image4_filename'],
                        'image5': line['image5'],
                        'image5_filename': line['image5_filename'],
                        'image6': line['image6'],
                        'image6_filename': line['image6_filename'],
                        'image7': line['image7'],
                        'image7_filename': line['image7_filename'],
                        'image8': line['image8'],
                        'image8_filename': line['image8_filename'],
                        'image9': line['image9'],
                        'image9_filename': line['image9_filename'],
                        'attachment_include': line['attachment_include'],
                    })]})
    
                    if line['vehicle_id']:
                        vehicle_id = line['vehicle_id']
                        date = line['date']
                        qty = line['qty']
                        description = line['description']
                        price_unit = line['price_unit']
                        amount = line['price_subtotal']
                        self.create_vehicle_cost_when_update(vehicle_id, expense_id, date, qty, description, price_unit, amount)
            return parent_id

    def create_vehicle_cost_when_update(self, vehicle_id=None, expense_id=None, date=None, qty=None, description=None, price_unit=None, amount=None):
        if vehicle_id and expense_id:
            vehicle = self.env['fleet.vehicle'].sudo().browse(vehicle_id)
#             odometer = vehicle.get_device_odometer()
#             last_consumption = self.env['compsuption.great.average'].sudo().search([('vehicle_id', '=', vehicle_id)], order='id desc', limit=1)
#             if last_consumption:
#                 consumption_last_odometer = last_consumption.odometer
#             else:
#                 consumption_last_odometer = 0
#             travel_odometer = odometer - consumption_last_odometer
            fuel_log_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': expense_id.employee_id.id,
                'fuel_tank_id': vehicle.fuel_tank.id,
                'liter': qty,
                'price_per_liter': price_unit,
                'amount': amount,
#                 'odometer': odometer,
                'date': date,
                'source_doc': expense_id.number,
            }
            last_odometer = vehicle.last_odometer
            current_odometer = vehicle.get_vehicle_odometer(vehicle)
            fuel_log_id = self.env['fleet.vehicle.log.fuel'].sudo().create(fuel_log_vals)
            if fuel_log_id.cost_id:
                fuel_log_id.cost_id.write({
                    'description': description,
                    'vendor_bill_ref': expense_id.number,
                    'odometer': last_odometer + current_odometer,
                })

            consumption_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': expense_id.employee_id.id,
                'source_doc': expense_id.number,
                'consumption_liter': qty,
                'modified_date': date,
                'last_odometer': last_odometer,
                'odometer': last_odometer + current_odometer,
#                 'last_odometer': consumption_last_odometer,
#                 'odometer': odometer,
#                 'travel_odometer': travel_odometer,
            }         
            fuel_consumption_id = self.env['compsuption.great.average'].sudo().create(consumption_vals)
            if vehicle.fuel_tank:
                fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
                    'filling_date': date,
                    'price_per_liter': price_unit,
                    'fuel_liter': qty,
                    'source_doc': expense_id.number,
                })
                vehicle.fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})

                fuel_filling_2nd = self.env['fuel.filling.history'].sudo().create({
                    'filling_date': date,
                    'price_per_liter': price_unit,
                    'fuel_liter': -qty,
                    'source_doc': expense_id.number,
                })
                vehicle.fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_2nd.id)]})
            return True
        else:
            return False

    def create_vehicle_cost(self, vehicle_id=None, employee_id=None, date=None, qty=None, description=None, price_unit=None, amount=None, code=None):
        if vehicle_id:
            vehicle = self.env['fleet.vehicle'].sudo().browse(vehicle_id)
#             odometer = vehicle.get_device_odometer()
#             last_consumption = self.env['compsuption.great.average'].sudo().search([('vehicle_id', '=', vehicle_id)], order='id desc', limit=1)
#             if last_consumption:
#                 consumption_last_odometer = last_consumption.odometer
#             else:
#                 consumption_last_odometer = 0
#             travel_odometer = odometer - consumption_last_odometer
            fuel_log_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': employee_id,
                'fuel_tank_id': vehicle.fuel_tank.id,
                'liter': qty,
                'price_per_liter': price_unit,
                'amount': amount,
#                 'odometer': odometer,
                'date': date,
                'source_doc': code,
            }
            fuel_log_id = self.env['fleet.vehicle.log.fuel'].sudo().create(fuel_log_vals)
            if fuel_log_id.cost_id:
                fuel_log_id.cost_id.write({
                    'description': description,
                    'vendor_bill_ref': code,
                })
            last_odometer = vehicle_id.last_odometer
            current_odometer = vehicle_id.get_vehicle_odometer(vehicle_id)
            consumption_vals = {
                'vehicle_id': vehicle_id,
                'employee_id': employee_id,
                'source_doc': code,
                'consumption_liter': qty,
                'modified_date': date,
                'last_odometer': last_odometer,
                'odometer': last_odometer + current_odometer,
#                 'last_odometer': consumption_last_odometer,
#                 'odometer': odometer,
#                 'travel_odometer': travel_odometer,
            }         
            fuel_consumption_id = self.env['compsuption.great.average'].sudo().create(consumption_vals)
            if vehicle.fuel_tank:
                fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
                    'filling_date': date,
                    'price_per_liter': price_unit,
                    'fuel_liter': qty,
                    'source_doc': code,
                })
                vehicle.fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})

                fuel_filling_2nd = self.env['fuel.filling.history'].sudo().create({
                    'filling_date': date,
                    'price_per_liter': price_unit,
                    'fuel_liter': -qty,
                    'source_doc': code,
                })
                vehicle.fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_2nd.id)]})
            return True
        else:
            return False

    def get_plan_trip_expense_emp_id(self, line_id=None, employee_id=None, status=None):
        if line_id and employee_id:
            employee_id = int(employee_id) 
            expense_line = self.env['trip.expense'].sudo().browse(line_id)
            if expense_line:
                expense_line.write({
                    'create_emp_id': employee_id
                })
                # if status == 'create':
                #     expense_line.write({
                #         'create_emp_id': employee_id
                #     })
                # elif status == 'edit':
                #     expense_line.write({
                #         'update_emp_id': employee_id
                #     })
                return True
        else:
            return False
    
    def get_day_trip_expense_emp_id(self, line_id=None, employee_id=None, status=None):
        if line_id and employee_id:
            employee_id = int(employee_id)
            expense_line = self.env['day.trip.expense'].sudo().browse(line_id)
            if expense_line:
                expense_line.write({
                    'create_emp_id': employee_id
                })
                # if status == 'create':
                #     expense_line.write({
                #         'create_emp_id': employee_id
                #     })
                # elif status == 'edit':
                #     expense_line.write({
                #         'update_emp_id': employee_id
                #     })
                return True
        else:
            return False
    
    def get_trip_expense_status(self, trip_id=None, status=None):
        if trip_id and status:
            domain = []
            if status == 'daytrip':
                domain = [('daytrip_id', '=', trip_id)]
            elif status == 'plantrip_product':
                domain = [('plantrip_product_id', '=', trip_id)]
            elif status == 'plantrip_waybill':
                domain = [('plantrip_waybill_id', '=', trip_id)]
            trip_expense = self.env['admin.trip.expense'].sudo().search(domain, limit=1)
            if trip_expense:
                return trip_expense.state   
            
    def get_route_list(self, trip_id=None, trip_type=None):
        result = []
        if trip_id and trip_type:
            if trip_type == 'plantrip_product':
                trip_obj = self.env['plan.trip.product'].sudo().browse(trip_id)
                if trip_obj and trip_obj.route_plan_ids:
                    for route in trip_obj.route_plan_ids:
                        result.append(route.route_id.id)
            elif trip_type == 'plantrip_waybill':
                trip_obj = self.env['plan.trip.waybill'].sudo().browse(trip_id)
                if trip_obj and trip_obj.route_plan_ids:
                    for route in trip_obj.route_plan_ids:
                        result.append(route.route_id.id)
        return result
        
    def add_fuel_in_line(self, parent_id=None, status=None, date=None, shop=None, product_id=None, location_id=None, slip_no=None, liter=None, price_unit=None):
        if parent_id and status:
            fuel_in_vals = {
                'date': date,
                'shop': shop,
                'product_id': product_id,
                'location_id': location_id,
                'slip_no': slip_no,
                'liter': liter,
                'price_unit': price_unit,
            }
            trip = None
#             odometer = 0
            if status == 'day_trip':
                trip = self.env['day.plan.trip'].sudo().browse(parent_id)
                fuel_in_vals['day_trip_id'] = parent_id
#                 odometer = trip.odometer
            elif status == 'plantrip_product':
                trip = self.env['plan.trip.product'].sudo().browse(parent_id)
                fuel_in_vals['trip_product_id'] = parent_id
#                 odometer = trip.last_odometer
            elif status == 'plantrip_waybill':
                trip = self.env['plan.trip.waybill'].sudo().browse(parent_id)
                fuel_in_vals['trip_waybill_id'] = parent_id
#                 odometer = trip.last_odometer
            fuel_in_id = self.env['trip.fuel.in'].sudo().create(fuel_in_vals)
            if fuel_in_id:
#                 current_odometer = trip.vehicle_id.get_device_odometer()
                vals = {
                    'vehicle_id': trip.vehicle_id.id,
                    'employee_id': trip.vehicle_id.incharge_id.id,
                    'fuel_tank_id': trip.vehicle_id.fuel_tank.id,
                    'liter': fuel_in_id.liter,
                    'amount': fuel_in_id.amount,
#                     'odometer': current_odometer,
#                     'previous_odometer': odometer,
#                     'prev_odo': odometer,
                    'date': fuel_in_id.date,
                    'inv_ref': fuel_in_id.slip_no,
                    'shop': fuel_in_id.shop,
                    'source_doc': trip.code,
                    'trip_fuel_in_line_id': fuel_in_id.id,
                }
                fuel_log_id = self.env['fleet.vehicle.log.fuel'].sudo().create(vals)
                if fuel_log_id.cost_id:
                    fuel_log_id.cost_id.write({
                        'source_doc': trip.code,
                        'trip_fuel_in_line_id': fuel_in_id.id,
                    })
                if trip.vehicle_id.fuel_tank:
                    fuel_tank = trip.vehicle_id.fuel_tank
                    current_liter = fuel_in_id.liter
                    for line in fuel_tank.fule_filling_history_ids:
                        current_liter += line.fuel_liter
                    if current_liter > fuel_tank.capacity:
                        raise ValidationError(_('Fuel liter reaches to its capacity. Consumed first.'))
                    else:
                        fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
                            'filling_date': fuel_in_id.date,
                            'price_per_liter': fuel_in_id.price_unit,
                            'fuel_liter': fuel_in_id.liter,
                            'source_doc': trip.code,
                            'trip_fuel_in_line_id': fuel_in_id.id,
                        })
                        fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})
            
            return {'id': fuel_in_id.id}
                
    def get_respective_manager_id(self, employee_id=None, status=None):
        if employee_id and status:
            employee_id = int(employee_id) 
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            if status in ('mid_year_self_assessment', 'year_end_self_assessment'):
                if employee.approve_manager:
                    return employee.approve_manager.id
                else:
                    return 0
            elif status in ('mid_year_manager_approve', 'year_end_manager_approve'):
                if employee.dotted_line_manager_id:
                    return employee.dotted_line_manager_id.id 
                else:
                    return 0
            elif status in ('mid_year_dotted_manager_approve', 'year_end_dotted_manager_approve'):
                if employee.branch_id.hr_manager_id:
                    return employee.branch_id.hr_manager_id.id
                else:
                    return 0
            else:
                return 0
    
    def action_pms_approve(self, parent_id=None, state=None):
        if parent_id and state:
            performance = self.env['employee.performance'].sudo().browse(parent_id)
            if state == 'mid_year_self_assessment':
                performance.action_mid_year_manager_approve()
            elif state == 'mid_year_manager_approve':
                performance.action_mid_year_dotted_manager_approve()
            elif state == 'mid_year_dotted_manager_approve':
                performance.action_mid_year_hr_approve()
            elif state == 'year_end_self_assessment':
                performance.action_year_end_manager_approve()
            elif state == 'year_end_manager_approve':
                performance.action_year_end_dotted_manager_approve()
            elif state == 'year_end_dotted_manager_approve':
                performance.action_year_end_hr_approve()
            return parent_id
    
    def approval_loan_requests(self, employee_id=None):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
#             date_range = self.get_fiscal_year(employee.company_id.id)
            loan_requests = self.env['hr.loan']
            domain = [('state', '=', 'waiting_approval_1')]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            md_ids = self.get_md_ids()
            if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids),
                                                                 ('manager_id.company_id', 'in',
                                                                  managing_director_companies.ids),
                                                                 ('direct_manager_id', '=', False)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                #branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
                #branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids),  ('manager_id.company_id', 'in',managing_director_companies.ids), ('direct_manager_id', '!=', False)])

                #direct_mgr_ids = [x.direct_manager_id.id for x in branches]
                #domain += ['|', ('employee_id', 'in', direct_mgr_ids),'|', ('employee_id.branch_id.direct_manager_id', 'in', direct_mgr_ids),
                #           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            if loan_requests:
                for loan in loan_requests:
                    result.append(loan.id)
        return result
    
    def approval_loan_requests_count(self, employee_id=None):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
#             date_range = self.get_fiscal_year(employee.company_id.id)
            loan_requests = self.env['hr.loan']
            domain = [('state', '=', 'waiting_approval_1')]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            md_ids = self.get_md_ids()
            if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
                direct_mgr_ids = [x.direct_manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', direct_mgr_ids),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            if loan_requests:
                for loan in loan_requests:
                    result.append(loan.id)
        return len(result)
    
    def approved_loan_requests(self, employee_id=None):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
#             date_range = self.get_fiscal_year(employee.company_id.id)
            loan_requests = self.env['hr.loan']
            domain = [('state', 'in', ('approve', 'refuse', 'verify'))]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            md_ids = self.get_md_ids()
            if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
                direct_mgr_ids = [x.direct_manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', direct_mgr_ids),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            if loan_requests:
                for loan in loan_requests:
                    result.append(loan.id)
        return result
    
    def approved_loan_requests_count(self, employee_id=None):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
#             date_range = self.get_fiscal_year(employee.company_id.id)
            loan_requests = self.env['hr.loan']
            domain = [('state', 'in', ('approve', 'refuse', 'verify'))]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            direct_mgr_branches = self.env['res.branch'].sudo().search([('direct_manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            md_ids = self.get_md_ids()
            if branch_manager_branches and not direct_mgr_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            elif branch_manager_branches and direct_mgr_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           '|', ('employee_id.branch_id.manager_id', '=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif direct_mgr_branches and not branch_manager_branches and not managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('id', 'in', direct_mgr_branches.ids),
                                                                 ('manager_id', 'not in', md_ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += [('employee_id', '!=', employee_id),
                           ('employee_id', 'in', branch_mgr_ids)]
                loan_requests = loan_requests.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids), ('manager_id.company_id', 'in', managing_director_companies.ids), ('direct_manager_id', '=', False)])
                direct_mgr_ids = [x.direct_manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', direct_mgr_ids),
                           ('employee_id.branch_id.manager_id', '=', employee_id)]
                loan_requests = loan_requests.sudo().search(domain)
            if loan_requests:
                for loan in loan_requests:
                    result.append(loan.id)
        return len(result)
    
    def approval_resignation(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            resignations = self.env['hr.resignation']
            domain = [('state', '=', 'confirm'), ('resign_confirm_date', '>=', date_range[0]), ('resign_confirm_date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            if resignations:
                for resignation in resignations:
                    result.append(resignation.id)
        return result
            
    def approval_resignation_count(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            resignations = self.env['hr.resignation']
            domain = [('state', '=', 'confirm'), ('resign_confirm_date', '>=', date_range[0]), ('resign_confirm_date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            if resignations:
                for resignation in resignations:
                    result.append(resignation.id)
        return len(result)
    
    def approved_resignation(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            resignations = self.env['hr.resignation']
            domain = [('state', 'in', ('approved', 'cancel')), ('resign_confirm_date', '>=', date_range[0]), ('resign_confirm_date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            if resignations:
                for resignation in resignations:
                    result.append(resignation.id)
        return result
    
    def approved_resignation_count(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            resignations = self.env['hr.resignation']
            domain = [('state', 'in', ('approved', 'cancel')), ('resign_confirm_date', '>=', date_range[0]), ('resign_confirm_date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                resignations = resignations.sudo().search(domain)
            if resignations:
                for resignation in resignations:
                    result.append(resignation.id)
        return len(result)
    
    def approval_employee_changes(self, employee_id):
        # import pdb
        # pdb.set_trace()
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            promotions = self.env['hr.promotion']
            domain = [('state', '=', 'first_approve'), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),('new_branch_id.manager_id', '=', employee_id)]
                # domain += [('employee_id', '!=', employee_id),
                #         ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            if promotions:
                for promotion in promotions:
                    result.append(promotion.id)
        return result

    def first_approval_employee_changes(self, employee_id):
        # import pdb
        # pdb.set_trace()
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            promotions = self.env['hr.promotion']
            domain = [('state', '=', 'request'), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),
                ('branch_id.manager_id', '=', employee_id)]
                # domain += [('employee_id', '!=', employee_id),
                #         ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            if promotions:
                for promotion in promotions:
                    result.append(promotion.id)
        return result

    def approval_employee_changes_count(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            promotions = self.env['hr.promotion']
            domain = [('state', 'in', ['request','first_approve']), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id), '|',('branch_id.manager_id', '=', employee_id),
                ('new_branch_id.manager_id', '=', employee_id)]
                # domain += [('employee_id', '!=', employee_id),
                #         ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            if promotions:
                for promotion in promotions:
                    result.append(promotion.id)
        return len(result)
    
    def approved_employee_changes(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            promotions = self.env['hr.promotion']
            domain = [('state', 'in', ('approve', 'cancel', 'done')), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),'|', ('branch_id.manager_id', '=', employee_id),
                ('new_branch_id.manager_id', '=', employee_id)]
                # domain += [('employee_id', '!=', employee_id),
                #         ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            if promotions:
                for promotion in promotions:
                    result.append(promotion.id)
        return result
    
    def approved_employee_changes_count(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            date_range = self.get_fiscal_year(employee.company_id.id)
            promotions = self.env['hr.promotion']
            domain = [('state', 'in', ('approve', 'cancel', 'done')), ('date', '>=', date_range[0]), ('date', '<=', date_range[1])]
            branch_manager_branches = self.env['res.branch'].sudo().search([('manager_id', '=', employee_id)])
            managing_director_companies = self.env['res.company'].sudo().search([('managing_director_id', '=', employee_id)])
            if branch_manager_branches and not managing_director_companies:
                domain += [('employee_id', '!=', employee_id),'|', ('branch_id.manager_id', '=', employee_id),
                ('new_branch_id.manager_id', '=', employee_id)]
                # domain += [('employee_id', '!=', employee_id),
                #         ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            elif managing_director_companies:
                branches = self.env['res.branch'].sudo().search([('company_id', 'in', managing_director_companies.ids)])
                branch_mgr_ids = [x.manager_id.id for x in branches]
                domain += ['|', ('employee_id', 'in', branch_mgr_ids),
                        ('employee_id.branch_id.manager_id', '=', employee_id)]
                promotions = promotions.sudo().search(domain)
            if promotions:
                for promotion in promotions:
                    result.append(promotion.id)
        return len(result)
    
    def get_pms_period(self):
        today_date = fields.Date.today()
        period = self.env['performance.date.range'].sudo().search([('date_start', '<=', today_date),
                                                                   ('date_end', '>=', today_date)], limit=1)
        return period
        
    def get_self_pms_ids(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            period = self.get_pms_period()
            if period:
                pms = self.env['employee.performance'].sudo().search([('employee_id', '=', employee_id),
                                                                      ('state', 'not in', ('draft', 'cancel')),
                                                                      ('pms_create_date', '>=', period.date_start),
                                                                      ('pms_create_date', '<=', period.date_end)])
                if pms:
                    for rec in pms:
                        result.append(rec.id)
        return result
    
    def get_fiscal_year(self, company_id):
        date_range = []
        if company_id:
            today_date = fields.Date.today()
            fiscal_year = self.env['hr.fiscal.year'].sudo().search([('date_from', '<=', today_date),
                                                                        ('date_to', '>=', today_date),
                                                                        ('company_id', '=', company_id)])
            if fiscal_year:
                date_range.append(str(fiscal_year.date_from))
                date_range.append(str(fiscal_year.date_to))
        return date_range
    
    def get_self_attendance(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            today_date = fields.Date.today()
            first_day_of_month = fields.Date.today().replace(day=1)
            one_month_before = today_date - timedelta(days=30)
            print("1st day of month : ", first_day_of_month)
            print("1 month before : ", one_month_before)
            self.env.cr.execute("""
                select id from hr_attendance  
                where employee_id = %s and check_in::date >= %s and create_date::date >= %s
                """,(employee_id,first_day_of_month,one_month_before,))
            attendance = set(res[0] for res in self.env.cr.fetchall())
            if attendance:
                attendances = self.env['hr.attendance'].sudo().search([('id', 'in', tuple(attendance))], order='check_in desc')
                if attendances:                
                    for att in attendances:
                        result.append(att.id)
        return result
    
    def get_employee_changes_list(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            user = employee.user_id
            if user:
                emp_changes = self.env['hr.promotion'].sudo().search(['|', ('company_id', 'in', user.company_ids.ids), ('new_company_id', 'in', user.company_ids.ids)])
                if emp_changes:
                    for rec in emp_changes:
                        result.append(rec.id)
            else:
                raise UserError(_('There is no user linked with current login employee.'))
        return result
    
    def get_employee_documents_list(self, employee_id):
        result = []
        if employee_id:
            employee_id = int(employee_id)
            emp_documents = self.env['hr.employee.document'].sudo().search([('employee_ref', '=', employee_id), ('state', '=', 'send_to_employee')])
            if emp_documents:
                for doc in emp_documents:
                    result.append(doc.id)
        return result
    
    def get_emp_document_attachments(self, doc_id):
        data_list = []
        if doc_id:
            doc = self.env['hr.employee.document'].sudo().browse(doc_id)
            if doc:
                for attachment in doc.doc_attachment_id:
                    data_dict = {
                         'data': attachment.datas,
                         'type': attachment.name
                    }
                    data_list.append(data_dict)
        result = {'attachment': data_list}
        return result
    
    def create_employee_changes(self, type=None, employee_id=None, company_id=None, branch_id=None, department_id=None, job_id=None, job_grade_id=None, salary_level_id=None, wage=None, date=None, new_company_id=None, new_branch_id=None, new_department_id=None, new_job_id=None, new_job_grade_id=None, new_salary_level_id=None, new_wage=None, new_approved_manager_id=None, note=None):
        if employee_id:
            vals = {
                'type': type,
                'employee_id': employee_id,
                'company_id': company_id,
                'branch_id': branch_id,
                'department_id': department_id,
                'job_id': job_id,
                'job_grade_id': job_grade_id,
                'salary_level_id': salary_level_id,
                'wage': wage,
                'date': date,
                'new_company_id': new_company_id,
                'new_branch_id': new_branch_id,
                'new_department_id': new_department_id,
                'new_job_id': new_job_id,
                'new_job_grade_id': new_job_grade_id,
                'new_salary_level_id': new_salary_level_id,
                'new_wage': new_wage,
                'new_approved_manager_id': new_approved_manager_id,
                'note': note,
            }
            emp_changes_id = self.env['hr.promotion'].sudo().create(vals)
            return emp_changes_id.id
    
    def get_employee_new_wage(self, new_job_grade_id=None, new_salary_level_id=None):
        if new_job_grade_id and new_salary_level_id:
            salary = self.env['hr.salary'].sudo().search([('job_grade_id', '=', new_job_grade_id),
                                                          ('salary_level_id', '=', new_salary_level_id)],
                                                          order='id desc', limit=1)
            if salary:
                return salary.salary
    
    def get_employee_job_grade(self, employee_id=None):
        result = {}
        if employee_id:
            employee_id = int(employee_id)
            employee = self.env['hr.employee'].sudo().browse(employee_id)
            contract = self.env['hr.contract'].sudo().search([('id', 'in', employee.contract_ids.ids), ('state', '=', 'open')], order='date_start desc', limit=1)
            if contract:
                result = {
                    'job_grade': contract.job_grade_id.id,
                    'job_grade_name': contract.job_grade_id.name,
                    'salary_level': contract.salary_level_id.id,
                    'salary_level_name': contract.salary_level_id.name,
                    'wage': contract.wage
                }
        return result
    
    def get_company_list(self, keyword=None):
        result = []
        domain = []
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        companies = self.env['res.company'].sudo().search(domain)
        for rec in companies.sorted(key=lambda x:x.name):
            result.append(rec.id)
        return result
    
    def get_branch_list(self, company_id=None, keyword=None):
        result = []
        domain = ['|', ('company_id', '=', int(company_id)), ('company_id', '=', False)]
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        branches = self.env['res.branch'].sudo().search(domain)
        for rec in branches:
            result.append(rec.id)
        return result
    
    def get_department_list(self, branch_id=None, keyword=None):
        result = []
        domain = ['|', ('branch_id', '=', int(branch_id)), ('branch_id', '=', False)]
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        departments = self.env['hr.department'].sudo().search(domain)
        for rec in departments:
            result.append(rec.id)
        return result
    
    def get_employee_list(self, company_id=None, branch_id=None, department_id=None, keyword=None):
        result = []
        domain = [('company_id', '=', int(company_id)), ('branch_id', '=', int(branch_id)), ('department_id', '=', int(department_id))]
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        employees = self.env['hr.employee'].sudo().search(domain)
        for rec in employees:
            name = '[' + str(rec.barcode) + '] ' + str(rec.name)
            data_dict = {
                 'id': rec.id,
                 'name': name,
                 'job_position': rec.job_id.name,
                 'job_id': rec.job_id.id
            }
            result.append(data_dict)
        return result
    
    def get_job_position_list(self, keyword=None):
        result = []
        domain = []
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        job_positions = self.env['hr.job'].sudo().search(domain)
        for rec in job_positions:
            result.append(rec.id)
        return result
    
    def get_job_grade_list(self, keyword=None):
        result = []
        domain = []
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        job_grades = self.env['job.grade'].sudo().search(domain)
        for rec in job_grades:
            result.append(rec.id)
        return result
    
    def get_salary_level_list(self, keyword=None):
        result = []
        domain = []
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        salary_levels = self.env['salary.level'].sudo().search(domain)
        for rec in salary_levels:
            result.append(rec.id)
        return result
    
    def get_approve_manager_list(self, company_id=None, branch_id=None, department_id=None, keyword=None):
        result = []
        domain = [('company_id', '=', int(company_id)), ('branch_id', '=', int(branch_id))]
        department_id = int(department_id)
        department = self.env['hr.department'].sudo().browse(department_id)
        if not department.parent_id:
            domain += [('department_id', '=', department_id)]
        else:
            dept_list = department.complete_name.split('/')
            parent_dept = dept_list[0].strip()
            depts = self.env['hr.department'].sudo().search(['|', ('name', '=', parent_dept), ('id', '=', department_id)])
            domain += [('department_id', 'in', depts.ids)]
        if keyword:
            domain += [('name', 'ilike', keyword)]            
        employees = self.env['hr.employee'].sudo().search(domain)
        for rec in employees:
            name = '[' + str(rec.barcode) + '] ' + str(rec.name)
            data_dict = {
                 'id': rec.id,
                 'name': name
            }
            result.append(data_dict)
        return result
            
    def get_expense_attachment_list(self, parent_id=None, expense=None):
        if parent_id and expense:
            result = []
            parent_id = int(parent_id)
            if expense == 'travel':
                travel_expense_lines = self.env['hr.travel.expense.line'].sudo().search([('line_id', '=', parent_id)])
                if travel_expense_lines:
                    for line in travel_expense_lines:
                        if line.attached_file:
                            result.append({
                                'expense_line_id': line.id,
                                'attachments': [line.attached_file, line.image1, line.image2, line.image3, line.image4, line.image5, line.image6, line.image7, line.image8, line.image9]
                            })
            elif expense == 'pocket':
                pocket_expense_lines = self.env['hr.pocket.expense.line'].sudo().search([('line_id', '=', parent_id)])
                if pocket_expense_lines:
                    for line in pocket_expense_lines:
                        if line.attached_file:
                            result.append({
                                'expense_line_id': line.id,
                                'attachments': [line.attached_file]
                            })
            elif expense == 'trip':
                trip_expense_lines = self.env['admin.trip.expense.line'].sudo().search([('expense_id', '=', parent_id)])
                if trip_expense_lines:
                    for line in trip_expense_lines:
                        if line.attached_file:
                            result.append({
                                'expense_line_id': line.id,
                                'attachments': [line.attached_file]
                            })
            return result