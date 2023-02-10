from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from geopy.distance import geodesic
from datetime import datetime, date, time, timedelta
from pytz import timezone, UTC
from odoo.addons.hr_attendance_ext.models.hr_attendance import time_to_float
import math
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import json
import requests
import logging
_logger = logging.getLogger(__name__)
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

class PlanTripProduct(models.Model):
    _name = 'plan.trip.product'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Plan Trip (With Product)'
    _rec_name = 'code'

    # def _default_created_by(self):
    #     return self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
    
    name = fields.Char(string='Name', required=False)
    code = fields.Char(string='Code')
    from_datetime = fields.Datetime(string='From Datetime',tracking=True)
    to_datetime = fields.Datetime(string='To Datetime',tracking=True)
    duration = fields.Float(string='Actual Duration', compute='_compute_duration', store=True)
    duration_hrs = fields.Float(string='Actual Duration', compute='_compute_duration', store=True)
    # created_by = fields.Many2one('hr.employee', string='Created by', default=lambda self: self._default_created_by())
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]",tracking=True)
    device_status = fields.Selection(related='vehicle_id.device_status', string='Device Status', store=True,
                                     readonly=True)
    current_speed = fields.Float(string="Current Speed", related='vehicle_id.current_speed', readonly=True)
    max_speed = fields.Float(string="Max Speed", related='vehicle_id.max_speed', readonly=True)
    average_speed = fields.Float(string="Average Speed", readonly=True)
    driver_id = fields.Many2one('hr.employee', string='Driver', domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]", store=True,tracking=True)
    spare1_id = fields.Many2one('hr.employee', string='Spare 1', domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]", store=True,tracking=True)
    spare2_id = fields.Many2one('hr.employee', string='Spare 2', domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]", store=True,tracking=True)
    product_lines = fields.One2many('trip.product.line', 'trip_product_id', string='Product')
    route_plan_ids = fields.One2many('trip.route.line', 'trip_product_id', string='Route', copy=True, auto_join=True)
    expense_ids = fields.One2many('trip.expense', 'trip_product_id', string='Expenses', copy=True, auto_join=True)
    consumption_ids = fields.One2many('trip.fuel.consumption', 'trip_product_id', string='Fuel Consumption', copy=True, auto_join=True)
    fuelin_ids = fields.One2many('trip.fuel.in', 'trip_product_id', string='Fuel In')
    product_ids = fields.One2many('trip.product.line','trip_product_id', string='Product')
    advanced_ids = fields.One2many('trip.advance', 'trip_product_id', string='Advance', copy=True, auto_join=True)
    request_allowance_lines = fields.One2many('travel.request.allowance', 'trip_product_id', string='Advance', copy=True, auto_join=True)
    approved_total = fields.Float('Approved Total', compute='_compute_total')
    actual_total = fields.Float('Actual Total', compute='_compute_total')
    driver_alw_hotel_qty = fields.Integer('Quantity')
    driver_alw_hotel_unit_price = fields.Integer('Unit Price', default=1)
    driver_alw_hotel_amount = fields.Integer('Amount', compute='_compute_driver_allowance')
    driver_alw_meal_qty = fields.Integer('Quantity')
    driver_alw_meal_unit_price = fields.Integer('Unit Price', default=1)
    driver_alw_meal_amount = fields.Integer('Amount', compute='_compute_driver_allowance')
    spare1_alw_hotel_qty = fields.Integer('Quantity')
    spare1_alw_hotel_unit_price = fields.Integer('Unit Price', default=1)
    spare1_alw_hotel_amount = fields.Integer('Amount', compute='_compute_spare1_allowance')
    spare1_alw_meal_qty = fields.Integer('Quantity')
    spare1_alw_meal_unit_price = fields.Integer('Unit Price', default=1)
    spare1_alw_meal_amount = fields.Integer('Amount', compute='_compute_spare1_allowance')
    spare2_alw_hotel_qty = fields.Integer('Quantity')
    spare2_alw_hotel_unit_price = fields.Integer('Unit Price', default=1)
    spare2_alw_hotel_amount = fields.Integer('Amount', compute='_compute_spare2_allowance')
    spare2_alw_meal_qty = fields.Integer('Quantity')
    spare2_alw_meal_unit_price = fields.Integer('Unit Price', default=1)
    spare2_alw_meal_amount = fields.Integer('Amount', compute='_compute_spare2_allowance')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('open', 'Open'),
        ('advance_request', 'Advance Request'),
        ('advance_withdraw', 'Advance Withdrew'),
        ('running', 'Running'),
        ('expense_claim','Expense Claim'),
        ('arrived', 'Arrived'),
        ('expense_submit', 'Expense Submit'),
        ('decline', 'Rejected'),
        ('close', 'Closed'),
        ('cancel', 'Cancel')],
        string='Status', readonly=True, copy=False, index=True, default='draft', track_visibility='always')
    last_odometer = fields.Float(string='Trip Odometer')
    current_odometer = fields.Float(string='Current Odometer')
    trip_distance = fields.Float(string='Trip Distance', compute='_compute_trip_distance')
    total_consumed_liter = fields.Integer('SUM Actual Consumption', compute='_compute_sum_actual_consumption')
    total_standard_liter = fields.Integer('SUM Standard Consumption', compute='_compute_sum_standard_consumption')
    avg_calculation = fields.Float(string='Consumption Rate (KM/Lit)', compute='_compute_avg_calculation')
    total_advance = fields.Float('Advanced Total', compute='_compute_total_advance')
    unit_expense = fields.Float('Unit Expense', compute='_compute_unit_expense')
    # advanced_request = fields.Float('Advanced Request', compute='_compute_total_advance')
    advance_allowed = fields.Float('Advance Allowed', required=True)
    payment_id = fields.Many2one('account.payment', string='Payment')
    plan_duration = fields.Float(string='Planned Duration (days)', compute='_compute_planned_duration', store=True)
    tyre_points = fields.Float(string='Tyre Points', compute='compute_tyre_and_engine_oil_points')
    engine_oil_points = fields.Float(string='Engine Oil Points', compute='compute_tyre_and_engine_oil_points')
    tyre_engine_oil_move_id = fields.Many2one('account.move', string='Accounting Entry for Tyre & Engine Oil Points')
    traccar_uniqueID = fields.Char(string = 'Trace Car UniqueID', related = 'vehicle_id.traccar_uniqueID')
    def get_tracksolid_token_parameter(self):
        parameter_token = self.env['ir.config_parameter'].sudo().get_param('track.solid_token')
        data = {}            
        if parameter_token:
            data['accessToken'] = parameter_token
            return data
    def get_tracksolid_token(self):
        url = "https://hk-open.tracksolidpro.com/route/rest"
        #url = "http://open.10000track.com/route/rest"
        #utc_current = self.convert_TZ_UTC(datetime.now())
        utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        data = False
        body = {'method': "jimi.oauth.token.get",
                'timestamp': utc_current,
                'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                'v': "0.9",
                'format': "json",
                'sign_method': "md5",
                'user_id': "winbrothersgroup",
                'user_pwd_md5': "8c570eeebcb92b0a9386679e1a026af5",
                'expires_in': 7200
                }

        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
            # 'authorization': "Basic REPLACE_BASIC_AUTH"
        }
        response = requests.request("POST", url, headers={}, params=body)
        if response.status_code == 200:
            data = json.loads(response.content.decode('utf-8'))
            code = data['code']
            if code == 1006:
                _logger.exception("Token error message", data['message'])
                return 'error'
            _logger.exception("GPS data.", data)
            print(json.loads(response.content.decode('utf-8')))
            if 'result' in data:
                data = data['result']
        parameter_token = self.env['ir.config_parameter'].sudo().get_param('track.solid_token')
        if data is not None:
            if not parameter_token:
                p_id = self.env['ir.config_parameter'].sudo().create(
                    {'key': 'track.solid_token', 'value': data['accessToken']})
            else:
                p_id = self.env['ir.config_parameter'].sudo().search([('key', '=', 'track.solid_token')])
                p_id.write({'value': data['accessToken']})
            return data
        else:
            data = {}
            parameter_token = self.env['ir.config_parameter'].sudo().get_param('track.solid_token')
            data['accessToken'] = parameter_token
            return data
    def show_current_localize(self):
        #token = self.get_tracksolid_token()
        token = self.get_tracksolid_token_parameter()
        if token == "error":
            raise ValidationError(
                _("Vehicle  API Error and please check with GPS Vendor.ERROR: 'Request frequency is too high today!''"))
        # utc_current = self.convert_TZ_UTC(datetime.now())
        utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if self.traccar_uniqueID and token != False:
            url = "https://hk-open.tracksolidpro.com/route/rest"
            #url = "http://open.10000track.com/route/rest"
            body = {'method': "jimi.device.location.URL.share",
                    'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                    'timestamp': utc_current,  # "2020-11-03 10:04:27",
                    'v': "0.9",
                    'sign_method': "md5",
                    'format': "json",
                    'access_token': token['accessToken'],  # 'ec6ec503d09e535d88ce58cc44a41755',

                    'imei': self.traccar_uniqueID,
                    'expires_in': 600
                    }

            headers = {
                'accept': "application/json",
                'content-type': "application/json"  # ,
            }
            response = requests.request("POST", url, headers={}, params=body)
            if response.status_code == 200:
                data = json.loads(response.content.decode('utf-8'))

                url_data = data['result']
                if url_data and url_data['URL']:
                    return {
                        'type': 'ir.actions.act_url',
                        'target': 'new',
                        'url': url_data['URL'],
                    }
                else:
                    raise ValidationError(
                        _("Vehicle  IMEI %s is offline , Error Msg: %s ") % (self.traccar_uniqueID, data['message']))
            else:
                token = self.get_tracksolid_token()
                if token == "error":
                    raise ValidationError(
                        _("Vehicle  API Error and please check with GPS Vendor.ERROR: 'Request frequency is too high today!''"))
                url = "https://hk-open.tracksolidpro.com/route/rest"
                #url = "http://open.10000track.com/route/rest"
                body = {'method': "jimi.device.location.URL.share",
                        'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                        'timestamp': utc_current,  # "2020-11-03 10:04:27",
                        'v': "0.9",
                        'sign_method': "md5",
                        'format': "json",
                        'access_token': token['accessToken'],  # 'ec6ec503d09e535d88ce58cc44a41755',
    
                        'imei': self.traccar_uniqueID,
                        'expires_in': 600
                        }
    
                headers = {
                    'accept': "application/json",
                    'content-type': "application/json"  # ,
                }
                response = requests.request("POST", url, headers={}, params=body)
                if response.status_code == 200:
                    data = json.loads(response.content.decode('utf-8'))
    
                    url_data = data['result']
                    if url_data and url_data['URL']:
                        return {
                            'type': 'ir.actions.act_url',
                            'target': 'new',
                            'url': url_data['URL'],
                        }
                    else:
                        raise ValidationError(
                            _("Vehicle  IMEI %s is offline , Error Msg: %s ") % (self.traccar_uniqueID, data['message']))

    @api.depends('trip_distance', 'vehicle_id.tyre_points_per_km', 'vehicle_id.engine_points_per_km')
    def compute_tyre_and_engine_oil_points(self):
        for trip in self:
            tyre_points = engine_oil_points = 0
            tyre_points = (trip.trip_distance / 1000) * trip.vehicle_id.tyre_points_per_km
            engine_oil_points = (trip.trip_distance / 150) * trip.vehicle_id.engine_points_per_km
            trip.tyre_points = tyre_points if tyre_points > 0 else  tyre_points * (-1)
            trip.engine_oil_points = engine_oil_points if engine_oil_points > 0 else engine_oil_points * (-1)

    @api.onchange('vehicle_id')
    def onchange_vehicle(self):
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.hr_driver_id
            self.spare1_id = self.vehicle_id.spare_id
    
    @api.depends('from_datetime', 'to_datetime')
    def _compute_duration(self):
        for record in self:
            days = 0
            hours = 0
            if record.from_datetime and record.to_datetime:
                time_diff = record.to_datetime - record.from_datetime
                days = time_diff.days
                hours = time_diff.seconds / 3600
            record.duration = days
            record.duration_hrs = hours
    
    @api.onchange('from_datetime', 'to_datetime')
    def onchange_dates(self):
        if self.from_datetime and self.to_datetime:
            if self.from_datetime > self.to_datetime:
                raise ValidationError(_('To Datetime should be greater than or equal to From Datetime.'))
              
    @api.depends('route_plan_ids')
    def _compute_planned_duration(self):
        for trip in self:
            planned_duration = 0
            if trip.route_plan_ids:
                for route in trip.route_plan_ids:
                    planned_duration += route.route_id.duration_days
            trip.plan_duration = planned_duration

    @api.constrains('advance_allowed', 'total_advance')
    @api.onchange('advance_allowed', 'total_advance')
    def check_total_advance(self):
        if self.advance_allowed and self.total_advance:
            if self.total_advance > self.advance_allowed:
                raise ValidationError("Total advance must not exceed allowed advance!")

    # @api.constrains('from_datetime', 'to_datetime')
   
    # def check_datetime(self):
    #     # import pdb
    #     # pdb.set_trace()
        # if self.from_datetime and self.to_datetime:
        #     if self.from_datetime > self.to_datetime:
        #         raise ValidationError("To Datetime should be greater than or equal to From Datetime.")
        #     if self.to_datetime > datetime.now().replace(microsecond=0):
        #         raise ValidationError("You can't save Plan Trip for this time.")
            

    @api.depends('last_odometer', 'current_odometer')
    def _compute_trip_distance(self):
        for record in self:
            record.trip_distance = record.current_odometer - record.last_odometer
    
    @api.depends('consumption_ids.consumed_liter')
    def _compute_sum_actual_consumption(self):
        for record in self:
            total_liter = 0
            if record.consumption_ids:
                for line in record.consumption_ids:
                    total_liter += line.consumed_liter
            record.total_consumed_liter = total_liter
    
    @api.depends('consumption_ids.standard_liter')
    def _compute_sum_standard_consumption(self):
        for record in self:
            total_liter = 0
            if record.consumption_ids:
                for line in record.consumption_ids:
                    total_liter += line.standard_liter
            record.total_standard_liter = total_liter
    
    @api.depends('trip_distance', 'total_consumed_liter')
    def _compute_avg_calculation(self):
        for record in self:
            total_consumed_liter = float(record.total_consumed_liter)
            trip_distance = record.trip_distance
            if total_consumed_liter != 0.0:
                record.avg_calculation = trip_distance / total_consumed_liter
            else:
                record.avg_calculation = 0.0

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft','submit','open'):
                raise UserError(_('Record(s) can\'t be deleted'))
        return super(PlanTripProduct, self).unlink()

    def action_submit(self):
        self.write({'state': 'submit'})
        if self.driver_id:            
            one_signal_values = {'employee_id': self.driver_id.branch_id.manager_id.id,
                                'contents': _('PLAN TRIP: To approve %s for %s.') % (self.code, self.driver_id.name),
                                'headings': _('WB B2B : TO APPROVE PLAN TRIP')}
            self.env['one.signal.notification.message'].create(one_signal_values)
            
    def get_att_in_out(self,employee_id):
        calendar = employee_id.resource_calendar_id
        tz = timezone(calendar.tz)
        yesterday = self.to_datetime + timedelta(hours=+6,minutes=+30) 
        dayofweek = yesterday.weekday()
        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', employee_id.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
        if employee_id.resource_calendar_id.two_weeks_calendar:
            week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
            domain += [('week_type', '=', str(week_type))]

        working_hours = self.env['resource.calendar.attendance'].sudo().search(domain) 
        if len(working_hours) == 1:
            for wh in working_hours:
                check_in = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_from)), is_dst=True).astimezone(tz=UTC)
                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                check_in = check_in #- timedelta(hours=+6,minutes=+30)
                check_out = check_out #+ timedelta(hours=+6,minutes=+30)
                check_in = check_in.strptime(str(check_in),"%Y-%m-%d %H:%M:%S+00:00")                                    
                check_in = check_in.strftime('%Y-%m-%d %H:%M:%S')
                check_in = datetime.strptime(check_in,'%Y-%m-%d %H:%M:%S')
                check_out = check_out.strptime(str(check_out),"%Y-%m-%d %H:%M:%S+00:00")                                    
                check_out = check_out.strftime('%Y-%m-%d %H:%M:%S')
                check_out = datetime.strptime(check_out,'%Y-%m-%d %H:%M:%S')
                
                return check_in,check_out

    def trip_check_out(self):
        day_count = 0
        ctx = self._context.copy()
        ctx.update({'trip':True})
        if self.to_datetime > self.from_datetime:
            delta = self.to_datetime.date() - self.from_datetime.date()
            day_count =delta.days
            today_date = self.from_datetime + timedelta(hours=+6,minutes=+30)
            date_start,date_stop = self.get_start_end_date(today_date.date())
            trip_end_time = self.to_datetime + timedelta(hours=+6,minutes=+30) 
            remark = self.code + '\n' + str(self.from_datetime+ timedelta(hours=+6,minutes=+30)) + '\n' +  str(self.to_datetime + timedelta(hours=+6,minutes=+30))
            if day_count == 0:
                if self.driver_id:
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.driver_id.id),
                                                                   ('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                    if att:
                        att.sudo().write({'remark':remark,'late_minutes':0.0,'early_out_minutes':0.0})
                    self.driver_id.write({'plan_trip_product_id':False})
#                     else:
#                         value = {'employee_id': self.driver_id.id, 'check_in': self.from_datetime,'plan_trip':True,
#                                  'check_out':self.to_datetime,'missed':False,'late_minutes':0.0,'early_out_minutes':0.0
#                                  }
#                         att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value) 
                if self.spare1_id:
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare1_id.id),
                                                                   ('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                    if att:
                        att.sudo().write({'remark':remark,'late_minutes':0.0,'early_out_minutes':0.0})
                    self.spare1_id.write({'plan_trip_product_id':False})
#                     else:
#                         value = {'employee_id': self.spare1_id.id, 'check_in': self.from_datetime,'plan_trip':True,
#                                  'check_out':self.to_datetime,'missed':False,'late_minutes':0.0,'early_out_minutes':0.0
#                                  }
#                         att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value)
                if self.spare2_id:
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare2_id.id),
                                                                   ('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                    if att:
                        att.sudo().write({'remark':remark,'late_minutes':0.0,'early_out_minutes':0.0})
                    self.spare2_id.write({'plan_trip_product_id':False})
#                     else:
#                         value = {'employee_id': self.spare2_id.id, 'check_in': self.from_datetime,'plan_trip':True,
#                                  'check_out':self.to_datetime,'missed':False,'late_minutes':0.0,'early_out_minutes':0.0
#                                  }
#                         att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value)
            else:  
                today_date = self.to_datetime + timedelta(hours=+6,minutes=+30)
                t_date_start,t_date_stop = self.get_start_end_date(today_date.date())
                if self.driver_id:
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.driver_id.id),
                                                                   ('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                    if att:
                        calendar = att.employee_id.resource_calendar_id
                        tz = timezone(calendar.tz)
                        yesterday = att.check_in + timedelta(hours=+6,minutes=+30) 
                        dayofweek = yesterday.weekday()
                        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', att.employee_id.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                        if att.employee_id.resource_calendar_id.two_weeks_calendar:
                            week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                            domain += [('week_type', '=', str(week_type))]
        
                        working_hours = self.env['resource.calendar.attendance'].sudo().search(domain) 
                        if len(working_hours) == 1:
                            for wh in working_hours:
                                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                att.sudo().write({'remark':remark,'late_minutes':0.0,'early_out_minutes':0.0})
                        
                    trip_absent_attendance = self.env['hr.attendance'].sudo().search([('check_in', '>=', self.from_datetime),
                                                            ('check_in', '<', self.to_datetime),
                                                            ('employee_id', '=', self.driver_id.id)], order='check_in desc')
                    for trip in trip_absent_attendance:
                        trip.sudo().write({'is_absent':False,'remark':remark,'plan_trip':True,'late_minutes':0.0,'early_out_minutes':0.0})
                    
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.driver_id.id),
                                                                   ('check_in','>=',t_date_start),('check_in', '<', t_date_stop)], order='check_in desc', limit=1)
                    dayofweek = today_date.weekday()
                    if dayofweek != 6:
                        check_in,check_out = self.get_att_in_out(self.driver_id)
                        if att:
                            if att.check_in <= self.to_datetime:
                                att.write({'remark':remark,'plan_trip':True})
                    self.driver_id.write({'plan_trip_product_id':False})
#                         else:
#                             if check_out <= trip_end_time:
#                                 value = {'employee_id': self.driver_id.id, 'check_in':check_in.strftime(DT),'check_out':self.to_datetime,'plan_trip':True}
#                             else:    
#                                 value = {'employee_id': self.driver_id.id, 'check_in': self.to_datetime,'plan_trip':True,'missed':True}
#                            
#                             att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value) 
                if self.spare1_id:
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare1_id.id),
                                                                   ('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                    if att:
                        calendar = att.employee_id.resource_calendar_id
                        tz = timezone(calendar.tz)
                        yesterday = att.check_in + timedelta(hours=+6,minutes=+30) 
                        dayofweek = yesterday.weekday()
                        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', att.employee_id.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                        if att.employee_id.resource_calendar_id.two_weeks_calendar:
                            week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                            domain += [('week_type', '=', str(week_type))]
        
                        working_hours = self.env['resource.calendar.attendance'].sudo().search(domain) 
                        if len(working_hours) == 1:
                            for wh in working_hours:
                                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                att.sudo().write({'remark':remark,'late_minutes':0.0,'early_out_minutes':0.0})
                                
                    
                    trip_absent_attendance = self.env['hr.attendance'].sudo().search([('check_in', '>=', self.from_datetime),
                                                            ('check_in', '<', self.to_datetime),
                                                            ('employee_id', '=', self.spare1_id.id)], order='check_in desc')
                    for trip in trip_absent_attendance:
                        trip.sudo().write({'is_absent':False,'remark':remark,'plan_trip':True,'late_minutes':0.0,'early_out_minutes':0.0})
                    
                    dayofweek = today_date.weekday()
                    if dayofweek != 6:    
                        check_in,check_out = self.get_att_in_out(self.spare1_id)
                        att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare1_id.id),
                                                                       ('check_in','>=',t_date_start),('check_in', '<', t_date_stop)], order='check_in desc', limit=1)
                        if att:
                            if att.check_in <= self.to_datetime:
                                att.write({'remark':remark,'plan_trip':True})
                        self.spare1_id.write({'plan_trip_product_id':False})
#                         else:
#                             if check_out <= trip_end_time:        
#                                 value = {'employee_id': self.spare1_id.id, 'check_in': self.to_datetime,'plan_trip':True,'missed':True}
#                             else:
#                                 value = {'employee_id': self.spare1_id.id, 'check_in':check_in.strftime(DT),'check_out': self.to_datetime,'plan_trip':True}
#                                 
#                             att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value)
                    
                if self.spare2_id:
                    att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare2_id.id),
                                                                   ('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                    if att:
                        calendar = att.employee_id.resource_calendar_id
                        tz = timezone(calendar.tz)
                        yesterday = att.check_in + timedelta(hours=+6,minutes=+30) 
                        dayofweek = yesterday.weekday()
                        domain = [('display_type', '!=', 'line_section'), ('calendar_id', '=', att.employee_id.resource_calendar_id.id), ('dayofweek', '=', str(dayofweek))]
                        if att.employee_id.resource_calendar_id.two_weeks_calendar:
                            week_type = int(math.floor((yesterday.toordinal() - 1) / 7) % 2)
                            domain += [('week_type', '=', str(week_type))]
        
                        working_hours = self.env['resource.calendar.attendance'].sudo().search(domain) 
                        if len(working_hours) == 1:
                            for wh in working_hours:
                                check_out = tz.localize(datetime.combine(fields.Datetime.to_datetime(yesterday), float_to_time(wh.hour_to)), is_dst=True).astimezone(tz=UTC)
                                att.sudo().write({'remark':remark,'late_minutes':0.0,'early_out_minutes':0.0})
                    
                    trip_absent_attendance = self.env['hr.attendance'].sudo().search([('check_in', '>=', self.from_datetime),
                                                            ('check_in', '<', self.to_datetime),
                                                            ('employee_id', '=', self.spare2_id.id)], order='check_in desc')
                    for trip in trip_absent_attendance:
                        trip.sudo().write({'is_absent':False,'remark':remark,'plan_trip':True,'late_minutes':0.0,'early_out_minutes':0.0})
                    dayofweek = today_date.weekday()
                    if dayofweek != 6:
                        check_in,check_out = self.get_att_in_out(self.spare2_id)
                        att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare2_id.id),
                                                                       ('check_in','>=',t_date_start),('check_in', '<', t_date_stop)], order='check_in desc', limit=1)
                        if att:
                            if att.check_in <= self.to_datetime:
                                att.write({'remark':remark,'day_trip':True})
#                         else:
#                             if check_out <= trip_end_time:    
#                                 value = {'employee_id': self.spare2_id.id, 'check_in': self.to_datetime,'plan_trip':True}
#                             else:
#                                 value = {'employee_id': self.spare2_id.id, 'check_in':check_in.strftime(DT), 'check_out': self.to_datetime,'plan_trip':True,'missed':True}
#                             att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value)     
                    
    def get_start_end_date(self,today_date):
        tz = timezone('Asia/Yangon')
        date_start = tz.localize((fields.Datetime.to_datetime(today_date)), is_dst=True).astimezone(tz=UTC)
        date_stop = tz.localize((datetime.combine(fields.Datetime.to_datetime(today_date), datetime.max.time())), is_dst=True).astimezone(tz=UTC)
        return date_start,date_stop
                
    def trip_check_in(self):
        day_count = 0
        ctx = self._context.copy()
        ctx.update({'trip':True})
        remark = self.code + '\n' + str(self.from_datetime + timedelta(hours=+6,minutes=+30)) + '\n' +  str(self.to_datetime + timedelta(hours=+6,minutes=+30))
        if self.to_datetime > self.from_datetime:
            delta = self.to_datetime.date() - self.from_datetime.date()
            day_count =delta.days
            today_date = self.from_datetime + timedelta(hours=+6,minutes=+30)
            date_start,date_stop = self.get_start_end_date(today_date.date())
            if self.driver_id:
                self.driver_id.write({'plan_trip_product_id':self.id})
                att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.driver_id.id),('check_in','>=',date_start),('check_in', '<', date_stop)], order='check_in desc', limit=1)
                if att:
                    att.write({'plan_trip':True,'remark':remark})
#                 if not att:                    
#                     value = {'employee_id': self.driver_id.id, 'check_in': self.from_datetime,'plan_trip':True,'missed':True}
#                     att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value)
#                 else:
#                     if att.check_in >= self.from_datetime:
#                         att.write({'plan_trip':True})
#                     else:
#                         att.write({'check_in':self.from_datetime,'plan_trip':True}) 
            if self.spare1_id:
                self.spare1_id.write({'plan_trip_product_id':self.id})
                att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare1_id.id),
                                                                ('check_in','>=',date_start),('check_in', '<', date_stop)], 
                                                                order='check_in desc', limit=1)
                if att:                    
                    att.write({'plan_trip':True,'remark':remark})
#                 if not att:                    
#                     value = {'employee_id': self.spare1_id.id, 'check_in': self.from_datetime,'plan_trip':True,'missed':True}
#                     att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value)
#                 else:
#                     if att.check_in >= self.from_datetime:
#                         att.write({'plan_trip':True})
#                     else:
#                         att.write({'check_in':self.from_datetime,'plan_trip':True})
            if self.spare2_id:
                self.spare2_id.write({'plan_trip_product_id':self.id})
                att = self.env['hr.attendance'].sudo().search([('employee_id','=',self.spare2_id.id),
                                                               ('check_in','>=',date_start),('check_in', '<', date_stop)], 
                                                               order='check_in desc', limit=1)
                if att:
                    att.write({'plan_trip':True,'remark':remark})
#                 if not att:                   
#                     value = {'employee_id': self.spare2_id.id, 'check_in': self.from_datetime,'plan_trip':True,'missed':True}
#                     att_id = self.env['hr.attendance'].sudo().with_context(ctx).create(value) 
#                 else:
#                     if att.check_in >= self.from_datetime:
#                         att.write({'plan_trip':True})
#                     else:
#                         att.write({'check_in':self.from_datetime,'plan_trip':True})
    def check_running_trip(self):
        old_from_date = self.from_datetime + timedelta(hours=+6, minutes=+30)
        today_date = datetime.now() + timedelta(hours=+6, minutes=+30)

        if old_from_date.date() != today_date.date():
            raise ValidationError(
                "You can't start trip from datetime must be today date. Not allowed back date or future date")

        if self.driver_id:
            if self.driver_id.day_trip_id and self.driver_id.day_trip_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s day trip %s is running.") % (
                self.driver_id.name, self.driver_id.day_trip_id.code))
            elif self.driver_id.plan_trip_waybill_id and self.driver_id.plan_trip_waybill_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s plan trip with waybill %s is running.") % (
                    self.driver_id.name, self.driver_id.plan_trip_waybill_id.code))
            elif self.driver_id.plan_trip_product_id and self.driver_id.plan_trip_product_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s plan trip with product %s is running.") % (
                    self.driver_id.name, self.driver_id.plan_trip_product_id.code))
        if self.spare1_id:
            if self.spare1_id.day_trip_id and self.spare1_id.day_trip_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s day trip %s is running.") % (
                self.spare1_id.name, self.spare1_id.day_trip_id.code))
            elif self.spare1_id.plan_trip_waybill_id and self.spare1_id.plan_trip_waybill_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s plan trip with waybill %s is running.") % (
                    self.spare1_id.name, self.spare1_id.plan_trip_waybill_id.code))
            elif self.spare1_id.plan_trip_product_id and self.spare1_id.plan_trip_product_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s plan trip with product %s is running.") % (
                    self.spare1_id.name, self.spare1_id.plan_trip_product_id.code))
        if self.spare2_id:
            if self.spare2_id.day_trip_id and self.spare2_id.day_trip_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s day trip %s is running.") % (
                self.spare2_id.name, self.spare2_id.day_trip_id.code))
            elif self.spare2_id.plan_trip_waybill_id and self.spare2_id.plan_trip_waybill_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s plan trip with waybill %s is running.") % (
                    self.spare2_id.name, self.spare2_id.plan_trip_waybill_id.code))
            elif self.spare2_id.plan_trip_product_id and self.spare2_id.plan_trip_product_id.state == 'running':
                raise ValidationError(_("Can't start trip as employee %s plan trip with product %s is running.") % (
                    self.spare2_id.name, self.spare2_id.plan_trip_product_id.code))

    def action_start(self):
        self.check_running_trip()
        self.trip_check_in()
        #last_odometer = self.vehicle_id.get_vehicle_odometer(self.vehicle_id)#self.vehicle_id.trip_odometer + self.vehicle_id.get_device_odometer()
        last_odometer=0
        avg_speed = 0#self.vehicle_id.get_device_avg_speed()
        #if avg_speed == False:
        #    avg_speed = self.vehicle_id.average_speed
        running_trips = self.env['plan.trip.product'].sudo().search([('state', '=', 'running'), 
                                                            ('vehicle_id', '=', self.vehicle_id.id)])
        if running_trips:
            raise UserError(_('You cannot start new trip without ending old trip!'))
        else:
            self.write({
                'state': 'running',
                'last_odometer': self.vehicle_id.trip_odometer,#self.vehicle_id.last_odometer,#self.vehicle_id.trip_odometer,
                # 'from_datetime': datetime.now(),
                'average_speed': avg_speed,
                })
            if self.vehicle_id:
                self.vehicle_id.write({
                    'trip_odometer': self.vehicle_id.last_odometer,#last_odometer,
                    'average_speed': avg_speed,
                })
            if self.fuelin_ids:
                for line in self.fuelin_ids:
                    vals = {
                        'vehicle_id': self.vehicle_id.id,
                        'employee_id': self.vehicle_id.incharge_id.id,
                        'fuel_tank_id': self.vehicle_id.fuel_tank.id,
                        'liter': line.liter,
                        'amount': line.amount,
                        'odometer': last_odometer,
                        'previous_odometer': self.last_odometer,
                        'prev_odo': self.last_odometer,
                        'date': line.date,
                        'inv_ref': line.slip_no,
                        'shop': line.shop,
                        'source_doc': self.code,
                        'trip_fuel_in_line_id': line.id,
                    }
                    fuel_log_id = self.env['fleet.vehicle.log.fuel'].sudo().create(vals)
                    if fuel_log_id.cost_id:
                        fuel_log_id.cost_id.write({
                            'source_doc': self.code,
                            'trip_fuel_in_line_id': line.id,
                        })
                    if self.vehicle_id.fuel_tank:
                        fuel_tank = self.vehicle_id.fuel_tank
                        current_liter = line.liter
                        for rec in fuel_tank.fule_filling_history_ids:
                            current_liter += rec.fuel_liter
                        if current_liter > fuel_tank.capacity:
                            raise ValidationError(_('Fuel liter reaches to its capacity. Consumed first.'))
                        else:
                            fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
                                'filling_date': line.date,
                                'price_per_liter': line.price_unit,
                                'fuel_liter': line.liter,
                                'source_doc': self.code,
                                'trip_fuel_in_line_id': line.id,
                            })
                            fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        self.write({'state': 'open'})
        
        if self.fuelin_ids:
            for line in self.fuelin_ids:
                line.write({'add_from_office': True})
                if line.location_id:
                    picking_type = self.env['stock.picking.type'].sudo().search([
                                    ('company_id', '=', line.location_id.company_id.id),
                                    ('code', '=', 'outgoing'),
                                    '|', 
                                    ('default_location_src_id', '=', line.location_id.id),
                                    ('default_location_src_id', '=', line.location_id.location_id.id)], limit=1)
                    customer_location = self.env['stock.location'].sudo().search([('usage', '=', 'customer')], limit=1)
                    vals = {
                        'state': 'draft',
                        'partner_id': line.location_id.company_id.partner_id.id,
                        'scheduled_date': line.date,
                        'origin': self.code,
                        'location_id': line.location_id.id,
                        'picking_type_id': picking_type.id,
                        'location_dest_id': customer_location.id,
                        # 'immediate_transfer': True
                    }
                    picking_obj = self.env['stock.picking'].sudo().create(vals)
                    if picking_obj:
                        move_vals = {
                            'name': line.product_id.name,
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.liter,
                            'product_uom': line.product_id.uom_id.id,
                            'location_id': picking_obj.location_id.id,
                            'location_dest_id': picking_obj.location_dest_id.id,
                            'picking_id': picking_obj.id,
                            'company_id': line.location_id.company_id.id,
                        }
                        self.env['stock.move'].sudo().create(move_vals)

        if self.driver_id:
            one_signal_values = {'employee_id': self.driver_id.id,
                                'contents': _('PLAN TRIP: %s approved plan trip.') % self.driver_id.branch_id.manager_id.name,
                                'headings': _('WB B2B : PLAN TRIP APPROVED')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        if self.spare1_id:
            one_signal_values = {'employee_id': self.spare1_id.id,
                                'contents': _('PLAN TRIP: %s approved plan trip.') % self.driver_id.branch_id.manager_id.name,
                                'headings': _('WB B2B : PLAN TRIP APPROVED')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        if self.spare2_id:
            one_signal_values = {'employee_id': self.spare2_id.id,
                                'contents': _('PLAN TRIP: %s approved plan trip.') % self.driver_id.branch_id.manager_id.name,
                                'headings': _('WB B2B : PLAN TRIP APPROVED')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def action_decline(self):
        self.write({'state': 'decline'})
    
    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_request_advance(self):
        journal = self.env['account.journal'].sudo().search([('company_id', '=', self.driver_id.company_id.id),
                                                    ('type', '=', 'bank'),
                                                    ('default_debit_account_id.user_type_id.type', '=', 'liquidity'),
                                                    ('default_credit_account_id.user_type_id.type', '=', 'liquidity')
                                                ], limit=1)
        if journal:
            bank_journal = journal.id
        method = self.env['account.payment.method'].sudo().search([('payment_type', '=', 'outbound')], limit=1)
        if method:
            payment_method = method.id
        values = {
                    'payment_type': 'outbound',
                    'partner_type': 'customer',
                    'partner_id': self.driver_id.address_home_id.id,
                    'company_id': self.driver_id.company_id.id,
                    'amount': self.total_advance,
                    'payment_date': fields.Date.today(),
                    'communication': 'Advance money',
                    'journal_id': bank_journal,
                    'payment_method_id': payment_method,
                    'plan_trip_product_id': self.id,
                    'reference': self.code,
                }
        payment = self.env['account.payment'].sudo().create(values)
        if payment:
            self.payment_id = payment.id
            
        self.state = 'advance_request'

    def _create_points_accounting_entry(self):
        config = self.env['fleet.accounting.config'].sudo().search([('vehicle_id', '=', self.vehicle_id.id),
                                                                    ('company_id', '=', self.company_id.id)])
        if config:
            if config.operation_journal_id:
                journal_id = config.operation_journal_id.id
                move_dict = {
                        'narration': '',
                        'ref': self.code,
                        'journal_id': journal_id,
                        'date': fields.Date.today(),
                    }
                line_ids = []                
                if self.tyre_points != 0:                    
                    partner_obj = self.env['res.partner'].sudo().search([('supplier_rank', '>', 0),
                                                                         ('company_id', '=', self.company_id.id),
                                                                         ('tyre_vendor', '=', True)], limit=1)
                    if partner_obj:
                        product_obj = self.env['product.product'].sudo().search([('company_id', '=', self.company_id.id),
                                                                                 ('is_tyre', '=', True),
                                                                                 ('name', 'ilike', 'tyre')], limit=1)
                        if product_obj:                            
                            if product_obj.property_account_expense_id:
                                debit_account_id = product_obj.property_account_expense_id.id
                            else:
                                raise ValidationError(_("Please define expense account for %s") % product_obj.name)   
                        else:
                            raise ValidationError(_("Please define tyre vendor for %s") % self.company_id.name)
                        analytic_tag_list = []
                        if config.analytic_tag_id:
                            analytic_tag_list.append(config.analytic_tag_id.id)  
                        if self.driver_id.department_id.analytic_tag_id: 
                            analytic_tag_list.append(self.driver_id.department_id.analytic_tag_id.id)
                        tyre_debit_line = {
                                            'name': self.code,
                                            'partner_id': partner_obj.id,
                                            'account_id': debit_account_id,
                                            'journal_id': journal_id,
                                            'date': fields.Date.today(),
                                            'debit': self.tyre_points,#product_obj.standard_price,
                                            'credit': 0,
                                            'analytic_account_id': self.branch_id.analytic_account_id.id if self.branch_id.analytic_account_id else None,
                                            'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                        }
                        line_ids.append(tyre_debit_line)
                        if partner_obj.property_account_payable_id:
                            credit_account_id = partner_obj.property_account_payable_id.id
                        else:
                            raise ValidationError(_("Please define payable account for vendor %s") % partner_obj.name)
                        tyre_credit_line = {
                                            'name': self.code,
                                            'partner_id': partner_obj.id,
                                            'account_id': credit_account_id,
                                            'journal_id': journal_id,
                                            'date': fields.Date.today(),
                                            'debit': 0,
                                            'credit': self.tyre_points,#product_obj.standard_price,
                                            'analytic_account_id': self.branch_id.analytic_account_id.id if self.branch_id.analytic_account_id else None,
                                            'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                        }
                        line_ids.append(tyre_credit_line)                        
                    else:
                        raise ValidationError("Please define tyre vendor!")
                if self.engine_oil_points != 0:                    
                    partner_obj = self.env['res.partner'].sudo().search([('supplier_rank', '>', 0),
                                                                         ('company_id', '=', self.company_id.id),
                                                                         ('engine_oil_vendor', '=', True)], limit=1)
                    if partner_obj:
                        product_obj = self.env['product.product'].sudo().search([('company_id', '=', self.company_id.id),
                                                                                 ('is_engine_oil', '=', True),
                                                                                 ('name', 'ilike', 'engine oil')], limit=1)
                        if product_obj:                            
                            if product_obj.property_account_expense_id:
                                debit_account_id = product_obj.property_account_expense_id.id
                            else:
                                raise ValidationError(_("Please define expense account for %s") % product_obj.name)   
                        else:
                            raise ValidationError(_("Please define engine oil vendor for %s") % self.company_id.name)
                        analytic_tag_list = []
                        if config.analytic_tag_id:
                            analytic_tag_list.append(config.analytic_tag_id.id)  
                        if self.driver_id.department_id.analytic_tag_id: 
                            analytic_tag_list.append(self.driver_id.department_id.analytic_tag_id.id)
                        engine_oil_debit_line = {
                                            'name': self.code,
                                            'partner_id': partner_obj.id,
                                            'account_id': debit_account_id,
                                            'journal_id': journal_id,
                                            'date': fields.Date.today(),
                                            'debit': self.engine_oil_points,#product_obj.standard_price,
                                            'credit': 0,
                                            'analytic_account_id': self.branch_id.analytic_account_id.id if self.branch_id.analytic_account_id else None,
                                            'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                        }
                        line_ids.append(engine_oil_debit_line)
                        if partner_obj.property_account_payable_id:
                            credit_account_id = partner_obj.property_account_payable_id.id
                        else:
                            raise ValidationError(_("Please define payable account for vendor %s") % partner_obj.name)
                        engine_oil_credit_line = {
                                            'name': self.code,
                                            'partner_id': partner_obj.id,
                                            'account_id': credit_account_id,
                                            'journal_id': journal_id,
                                            'date': fields.Date.today(),
                                            'debit': 0,
                                            'credit': self.engine_oil_points,#product_obj.standard_price,
                                            'analytic_account_id': self.branch_id.analytic_account_id.id if self.branch_id.analytic_account_id else None,
                                            'analytic_tag_ids': [(6, 0, analytic_tag_list)]
                                        }
                        line_ids.append(engine_oil_credit_line)                        
                    else:
                        raise ValidationError("Please define engine oil vendor!")
                if len(line_ids) > 0:
                    move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                    move = self.env['account.move'].create(move_dict)   
                    self.write({'tyre_engine_oil_move_id': move.id})                 
            else:
                raise ValidationError("Please define operation journal for vehicle!")
        else:
            raise ValidationError("Please define accounting configuration for vehicle!")

    def check_end_trip_delay(self):
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        today_date = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz).date()
        if self.to_datetime:

            end_date = self.to_datetime.date() + timedelta(days=+2)
            if end_date < today_date:

                if not self.user_has_groups('route_plan.group_allowed_endtrip'):
                    raise ValidationError(_("You don't have access right for end trip as trip over delay 2 days !. Please contact your Manager."))

    def update_fuel_consumption_odometer(self,last_odometer,current_odometer):
        i = 0
        for consumption in self.consumption_ids:

            compsuption_id = self.env['compsuption.great.average'].search([('trip_consumption_line_id', '=', consumption.id)],limit=1)

            if compsuption_id:
                i += 1
                if i == len(self.consumption_ids):
                    compsuption_id.write({'last_odometer':last_odometer,'odometer':last_odometer + current_odometer})
                else:
                    compsuption_id.write({'last_odometer': self.last_odometer, 'odometer': self.last_odometer})
        fuel_log = 0
        for line in self.fuelin_ids:
            fuel_id = self.env['fleet.vehicle.log.fuel'].search([('trip_fuel_in_line_id','=',line.id)])
            if fuel_id:
                fuel_log += 1
                if fuel_log == len(self.fuelin_ids):
                    fuel_id.write({'odometer': last_odometer + current_odometer})
                else:
                    fuel_id.write({'odometer': self.last_odometer})

    def action_end(self):
        self.check_end_trip_delay()
        last_odometer = self.vehicle_id.last_odometer
        #current_odometer = self.vehicle_id.get_vehicle_odometer(self.vehicle_id)#self.vehicle_id.trip_odometer + self.vehicle_id.get_device_odometer()
        current_odometer=0
        self.update_fuel_consumption_odometer(last_odometer, current_odometer)
        avg_speed = 0#self.vehicle_id.get_device_avg_speed()
        if self.from_datetime and self.to_datetime:
            if self.from_datetime > self.to_datetime:
                raise ValidationError("To Datetime should be greater than or equal to From Datetime.")
            if self.to_datetime > datetime.now().replace(microsecond=0):
                raise ValidationError("You can't save Plan Trip for this time.")
        #if avg_speed == False:
        #    avg_speed = self.vehicle_id.average_speed
        self.trip_check_out()
        self.write({
            'state': 'expense_claim',
            'current_odometer': self.vehicle_id.last_odometer,#current_odometer,
            # 'to_datetime': datetime.now(),
            'average_speed': avg_speed,
            })
        if self.vehicle_id:
            self.vehicle_id.write({
                'trip_odometer': self.vehicle_id.last_odometer,#current_odometer,
                'average_speed': avg_speed,
            })

#         if self.fuelin_ids:
#             vehicle = self.env['fleet.vehicle'].sudo().search([('id', '=', self.vehicle_id.id)])
#             if vehicle:
#                 for line in self.fuelin_ids:
#                     vals = {
#                         'vehicle_id': self.vehicle_id.id,
#                         'employee_id': self.vehicle_id.incharge_id.id,
#                         'fuel_tank_id': self.vehicle_id.fuel_tank.id,
#                         'liter': line.liter,
#                         'amount': line.amount,
#                         'odometer': self.current_odometer,
#                         'previous_odometer': self.last_odometer,
#                         'prev_odo': self.last_odometer,
#                         'date': line.date,
#                         'inv_ref': line.slip_no,
#                         'shop': line.shop,
#                         'source_doc': self.code,
#                     }
#                     fuel_log_id = self.env['fleet.vehicle.log.fuel'].sudo().create(vals)
#                     if fuel_log_id.cost_id:
#                         fuel_log_id.cost_id.write({
#                             'source_doc': self.code,
#                         })
# 
#                 if vehicle.fuel_tank:
#                     fuel_tank = vehicle.fuel_tank
#                     for line in self.fuelin_ids:
#                         fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
#                             'filling_date': line.date,
#                             'price_per_liter': line.price_unit,
#                             'fuel_liter': line.liter,
#                             'source_doc': self.code,
#                         })
#                         fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})

#         if self.consumption_ids:
#             for line in self.consumption_ids:
#                 print("##### ", line.date.date())
#                 filling_vals = {
#                     'vehicle_id': self.vehicle_id.id,
#                     'employee_id': self.driver_id.id,
#                     'source_doc': self.code,
#                     'consumption_liter': line.consumed_liter,
#                     'modified_date': line.date.date() if line.date else fields.Date.today(),
#                     'odometer': self.current_odometer,
#                 }         
#                 self.env['compsuption.great.average'].sudo().create(filling_vals)
#             if self.vehicle_id.fuel_tank:
#                 fuel_tank = self.vehicle_id.fuel_tank
#                 total_amount = total_liter = price_unit = 0
#                 for line in fuel_tank.fule_filling_history_ids:
#                     total_amount += line.amount
#                     total_liter += line.fuel_liter
#                 if total_liter != 0:
#                     price_unit = total_amount / total_liter
#                 for line in self.consumption_ids:
#                     fuel_filling_id = self.env['fuel.filling.history'].sudo().create({
#                         'filling_date': line.date.date() if line.date else fields.Date.today(),
#                         'price_per_liter': price_unit,
#                         'fuel_liter': -line.consumed_liter,
#                         'source_doc': self.code,
#                     })
#                     fuel_tank.sudo().write({'fule_filling_history_ids': [(4, fuel_filling_id.id)]})



    def action_expense_claim(self):
        self.write({
            'state': 'close',

        })
        if self.expense_ids:
            trip_expense_obj = self.env['admin.trip.expense']
            data = {
                'date': fields.Date.today(),
                'employee_id': self.driver_id.id,
                'company_id': self.company_id.id,
                'source_doc': self.code,
                'advanced_money': self.total_advance,#self.advance_allowed,
                'state': 'submit',
                'plantrip_product_id': self.id,
                'payment_id': self.payment_id.id,
                'payment_amount': self.payment_id.amount,
            }
            trip_expense = trip_expense_obj.sudo().create(data)
            for line in self.expense_ids:
                attachment_include = False
                if line.attached_file:
                    attachment_include = True
                trip_expense.sudo().write({
                            'trip_expense_lines': [(0, 0, {
                                'expense_id': trip_expense.id,
                                'date': fields.Date.today(),
                                'categ_id': line.route_expense_id.product_id.product_tmpl_id.categ_id.id,
                                'product_id': line.route_expense_id.product_id.id,
                                'description': line.route_expense_id.name,
                                'qty': 1,
                                'price_unit': line.actual_amount,
                                'price_subtotal': line.actual_amount,
                                'over_amount': line.over_amount,
                                'attached_file': line.attached_file,
                                'attachment_include': attachment_include,
                                'vehicle_id': self.vehicle_id.id,
                                'analytic_account_id': self.driver_id.branch_id.analytic_account_id.id,
                                'analytic_tag_ids': [(6, 0, [x.id for x in self.driver_id.department_id.analytic_tag_id])],
                            })]
                        })
            self.trip_expense_id = trip_expense.id
        self.compute_tyre_and_engine_oil_points()
        if self.tyre_points != 0 or self.engine_oil_points != 0:
            self._create_points_accounting_entry()

        if self.tyre_points != 0:
            tyre_vals = {
                'vehicle_id': self.vehicle_id.id,
                'date': fields.Date.today(),
                'used_points': self.tyre_points,
                'source_doc': self.code,
            }
            self.env['fleet.tyre.history'].sudo().create(tyre_vals)

    @api.depends('driver_alw_hotel_qty', 'driver_alw_hotel_unit_price', 'driver_alw_meal_qty', 'driver_alw_meal_unit_price')
    def _compute_driver_allowance(self):
        for rec in self:
            rec.driver_alw_hotel_amount = 0
            if rec.driver_alw_hotel_qty and rec.driver_alw_hotel_unit_price:
                rec.driver_alw_hotel_amount = rec.driver_alw_hotel_qty * rec.driver_alw_hotel_unit_price
            rec.driver_alw_meal_amount = 0
            if rec.driver_alw_meal_qty and rec.driver_alw_meal_unit_price:
                rec.driver_alw_meal_amount = rec.driver_alw_meal_qty * rec.driver_alw_meal_unit_price

    @api.depends('spare1_alw_hotel_qty', 'spare1_alw_hotel_unit_price', 'spare1_alw_meal_qty', 'spare1_alw_meal_unit_price')
    def _compute_spare1_allowance(self):
        for rec in self:
            rec.spare1_alw_hotel_amount = 0
            if rec.spare1_alw_hotel_qty and rec.spare1_alw_hotel_unit_price:
                rec.spare1_alw_hotel_amount = rec.spare1_alw_hotel_qty * rec.spare1_alw_hotel_unit_price
            rec.spare1_alw_meal_amount = 0
            if rec.spare1_alw_meal_qty and rec.spare1_alw_meal_unit_price:
                rec.spare1_alw_meal_amount = rec.spare1_alw_meal_qty * rec.spare1_alw_meal_unit_price

    @api.depends('spare2_alw_hotel_qty', 'spare2_alw_hotel_unit_price', 'spare2_alw_meal_qty', 'spare2_alw_meal_unit_price')
    def _compute_spare2_allowance(self):
        for rec in self:
            rec.spare2_alw_hotel_amount = 0
            if rec.spare2_alw_hotel_qty and rec.spare2_alw_hotel_unit_price:
                rec.spare2_alw_hotel_amount = rec.spare2_alw_hotel_qty * rec.spare2_alw_hotel_unit_price
            rec.spare2_alw_meal_amount = 0
            if rec.spare2_alw_meal_qty and rec.spare2_alw_meal_unit_price:
                rec.spare2_alw_meal_amount = rec.spare2_alw_meal_qty * rec.spare2_alw_meal_unit_price

    @api.depends('advanced_ids', 'expense_ids')
    def _compute_total(self):
        for record in self:
            approved_total = actual_total = 0
            for adv in record.advanced_ids:
                approved_total += adv.approved_advance
            for exp in record.expense_ids:
                actual_total += exp.actual_amount
            record.approved_total = approved_total
            record.actual_total = actual_total
    
    @api.depends('product_ids', 'expense_ids', 'consumption_ids', 'fuelin_ids')    
    def _compute_unit_expense(self):
        for record in self:
            total_unit_expense = product_count = total_consumed_qty = amount = liter = price = 0
            for allowance in record.expense_ids:
                if allowance.route_expense_id.product_id.product_tmpl_id.exclude is False:
                    total_unit_expense += allowance.actual_amount
            for consumption in record.consumption_ids:
                total_consumed_qty += consumption.consumed_liter
            if record.vehicle_id.fuel_tank:
                for line in record.vehicle_id.fuel_tank.fule_filling_history_ids:
                    amount += line.amount 
                    liter += line.fuel_liter
            if liter != 0:
                price = amount / liter
            total_unit_expense += total_consumed_qty * price
            for product in record.product_ids:
                product_count += product.quantity
            if product_count > 0 :
                total_unit_expense = total_unit_expense / product_count
            record.unit_expense = total_unit_expense
        # for record in self:
        #     total_unit_expense = product_count = 0
        #     for allowance in record.expense_ids:
        #         print("expense_ids>>>",allowance.actual_amount)
        #         total_unit_expense += allowance.actual_amount
        #     for product in record.product_ids:
        #         print("product>>>",product.quantity)
        #         product_count += product.quantity
        #     if product_count > 0 :
        #         total_unit_expense = total_unit_expense / product_count
        #     record.unit_expense = total_unit_expense
            
    @api.depends('request_allowance_lines.total_amount')
    def _compute_total_advance(self):
        for record in self:
            total_advance = 0
            for allowance in record.request_allowance_lines:
                total_advance += allowance.total_amount
            record.total_advance = total_advance
            # record.advanced_request = total_advance

    @api.model
    def create(self, vals):
        driver = vals.get('driver_id')
        spare1 = vals.get('spare1_id')
        spare2 = vals.get('spare2_id')
        vehicle = vals.get('vehicle_id')
        from_datetime = vals.get('from_datetime')
        to_datetime = vals.get('to_datetime')
        from_date = datetime.strptime(str(from_datetime), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        to_date = datetime.strptime(str(to_datetime), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        driver_obj = self.env['hr.employee'].sudo().browse(driver)
        spare1_obj = self.env['hr.employee'].sudo().browse(spare1)
        spare2_obj = self.env['hr.employee'].sudo().browse(spare2)
        vehicle_obj = self.env['fleet.vehicle'].sudo().browse(vehicle)
        lists = []
        if driver:
            lists.append(driver)
        if spare1:
            lists.append(spare1)
        if spare2:
            lists.append(spare2)
        
        running_trips = self.env['plan.trip.product'].sudo().search([('state', '=', 'running'),
                                                            '|', '|', '|', ('vehicle_id', '=', vehicle),
                                                            ('driver_id', 'in', lists),
                                                            ('spare1_id', 'in', lists),
                                                            ('spare2_id', 'in', lists)
                                                        ])
        if running_trips:
            raise UserError(_('There is a running trip with the same vehicle/driver/spare! You cannot create new trip without ending old trip!'))

        driver_same_plan_trip = self.env['plan.trip.product'].sudo().search([('vehicle_id', '=', vehicle),
                                                            ('state', 'not in', ['close','cancel']),
                                                            ('from_datetime', '>=', str(from_date) + ' 00:00:00'),
                                                            ('from_datetime', '<=', str(from_date) + ' 23:59:59'),
                                                            ('to_datetime', '>=', str(to_date) + ' 00:00:00'),
                                                            ('to_datetime', '<=', str(to_date) + ' 23:59:59'),
                                                            '|', '|', ('driver_id', '=', driver), 
                                                            ('spare1_id', '=', driver),
                                                            ('spare2_id', '=', driver)
                                                        ])
        if driver_same_plan_trip:
            raise UserError(_('You cannot create another record for %s on the same day for %s!') % (driver_obj.name, vehicle_obj.name))
        
        spare1_same_plan_trip = self.env['plan.trip.product'].sudo().search([('vehicle_id', '=', vehicle),
                                                            ('state', 'not in', ['close','cancel']),
                                                            ('from_datetime', '>=', str(from_date) + ' 00:00:00'),
                                                            ('from_datetime', '<=', str(from_date) + ' 23:59:59'),
                                                            ('to_datetime', '>=', str(to_date) + ' 00:00:00'),
                                                            ('to_datetime', '<=', str(to_date) + ' 23:59:59'),
                                                            '|', '|', ('driver_id', '=', spare1), 
                                                            ('spare1_id', '=', spare1),
                                                            ('spare2_id', '=', spare1)
                                                        ])
        if spare1_same_plan_trip:
            raise UserError(_('You cannot create another record for %s on the same day for %s!') % (spare1_obj.name, vehicle_obj.name))
        
        spare2_same_plan_trip = self.env['plan.trip.product'].sudo().search([('vehicle_id', '=', vehicle),
                                                            ('state', 'not in', ['close','cancel']),
                                                            ('from_datetime', '>=', str(from_date) + ' 00:00:00'),
                                                            ('from_datetime', '<=', str(from_date) + ' 23:59:59'),
                                                            ('to_datetime', '>=', str(to_date) + ' 00:00:00'),
                                                            ('to_datetime', '<=', str(to_date) + ' 23:59:59'),
                                                            '|', '|', ('driver_id', '=', spare2), 
                                                            ('spare1_id', '=', spare2),
                                                            ('spare2_id', '=', spare2)
                                                        ])
        if spare2_same_plan_trip:
            raise UserError(_('You cannot create another record for %s on the same day for %s!') % (spare2_obj.name, vehicle_obj.name))

        if 'company_id' in vals:
            code = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('plan.trip.product.code')
            vals['code'] = code
        else:
            code = self.env['ir.sequence'].next_by_code('plan.trip.product.code')
            vals['code'] = code
        return super(PlanTripProduct, self).create(vals)
    
    # @api.onchange('vehicle_id')
    # def onchange_vehicle(self):
    #     if self.vehicle_id:
    #         self.driver_id = self.vehicle_id.driver_id.id
    def get_expense_line(self,route_id):
        trip_expense_line = self.env['trip.expense']

        if self.state in ['advance_request','advance_withdraw','running']:

            for expense in self.expense_ids.filtered(
                    lambda aml: aml.route_id.id == route_id.id):
                trip_expense_line += trip_expense_line.new({'route_id': expense.route_id.id,
                                                            'trip_product_id': expense.trip_product_id.id,
                                                            'actual_amount': expense.actual_amount,
                                                            'description':expense.description,
                                                            'route_expense_id':expense.route_expense_id.id,
                                                            'attached_file': expense.attached_file,
                                                            #'update_emp_id':expense.update_emp_id.id or False,
                                                            #'create_emp_id':expense.create_emp_id.id or False,
                                                            })
            return trip_expense_line


        else:
            return trip_expense_line

    @api.onchange('route_plan_ids')
    def onchange_route_plan_ids(self):
        expense_lines = self.env['trip.expense']
        consumption_lines = self.env['trip.fuel.consumption']
        advanced_lines = self.env['trip.advance']
        name = ''
        advance_allowed = 0
        if self.route_plan_ids:
            # create_emp = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            for line in self.route_plan_ids:
                print("line>>>>",line.id)
                if not name:
                    name = '(' + line.route_id.name + ')'
                else:
                    name += ' - (' + line.route_id.name + ')'
                # expense_exit_or_not = self.get_expense_line(line.route_id)
                # if expense_exit_or_not:
                #     expense_lines += expense_exit_or_not
                #     consumption_lines += consumption_lines.new({'route_id': line.route_id.id})
                #     advanced_lines += advanced_lines.new({'route_id': line.route_id.id})
                #     advance_allowed += line.route_id.approved_advance
                #     continue
                for expense in line.route_id.expense_ids:
                    expense_lines += expense_lines.new({'route_id': line.route_id.id, 'route_expense_id': expense.id})
                consumption_lines += consumption_lines.new({'route_id': line.route_id.id})
                advanced_lines += advanced_lines.new({'route_id': line.route_id.id})
                advance_allowed += line.route_id.approved_advance
            self.name = name
            self.expense_ids = expense_lines
            self.consumption_ids = consumption_lines
            self.advanced_ids = advanced_lines
            self.advance_allowed = advance_allowed

    @api.constrains('route_plan_ids')
    def check_route_plan_ids(self):
        for record in self:
            if len(record.route_plan_ids) == 0:
                raise UserError('You cannot create without any route!')


class TravelRequestAllowance(models.Model):
    _inherit = 'travel.request.allowance'
    
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)   
    
