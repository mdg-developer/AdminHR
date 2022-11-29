# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import requests
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# import datetime
import time
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from bokeh.plotting import gmap
from bokeh.embed import components
from bokeh.models import (GMapPlot, GMapOptions, ColumnDataSource, Line, Circle,
                          Range1d, PanTool, WheelZoomTool, HoverTool, SaveTool)

from odoo import api, fields, models, tools, osv, exceptions, SUPERUSER_ID, _
from odoo.exceptions import UserError
import math
from pprint import pprint
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


def convert_hr_mm(millis):
    seconds = (millis / 1000) % 60
    seconds = int(seconds)
    minutes = (millis / (1000 * 60)) % 60
    minutes = int(minutes)
    hours = (millis / (1000 * 60 * 60))  # %24
    return str(hours) + '-h'
    # return str(math.ceil(hours))+ 'h-' + str(minutes) + ' m'


def get_device_summary(cookie, device_id, group_id):
    params = {'deviceId': [device_id], 'groupId': [group_id], 'from': '2019-11-14T00:00:00.000Z',
              'to': '2019-11-14T23:59:00.000Z'}
    # params = {'deviceid': device_id,'groupId':[group_id], 'from' : '2000-01-01T00:00:00.000Z', 'to' : '2050-01-01T00:00:00.000Z'}
    headers = {'Cookie': cookie[0], 'Content-Type': 'application/json', 'Accept': 'application/json'}

    response = requests.get(cookie[1] + '/api/reports/summary', headers=headers, params=params)
    result = 0, 0, 0, None, None

    for reportsummary in response.json():
        if reportsummary['deviceId'] == device_id:
            totalDistance = 0
            if 'attributes' in reportsummary and reportsummary['attributes'].get('totalDistance',
                                                                                 False): totalDistance = reportsummary[
                'attributes'].get('totalDistance', 0)
            result = float(reportsummary['averageSpeed']), float(reportsummary['maxSpeed']), float(
                reportsummary['spentFuel']), reportsummary['engineHours'], totalDistance
    return result


def get_trip_summary(cookie, device_id, group_id, from_date, to_date):
    final_values = []  # {}
    # params = {'deviceId': [device_id],'groupId':[group_id],'from' : '2019-11-14T00:00:00.000Z', 'to' : '2019-11-14T23:59:00.000Z'}
    params = {'deviceId': [device_id], 'groupId': [group_id], 'from': from_date, 'to': to_date}
    headers = {'Cookie': cookie[0], 'Content-Type': 'application/json', 'Accept': 'application/json'}

    response = requests.get(cookie[1] + '/api/reports/trips', headers=headers, params=params)
    result = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, False, None, False, None, 0
    if response.status_code == 200:
        for reportsummary in response.json():
            if reportsummary['deviceId'] == device_id:
                totalDistance = 0
                # if 'items' in reportsummary and reportsummary['items'].get('distance', False): totalDistance = reportsummary['items'].get('duration', 0)
                # result = float(reportsummary['averageSpeed']), float(reportsummary['maxSpeed']),float(reportsummary['spentFuel']),reportsummary['startAddress'],  reportsummary['duration']
                final_values.append({
                    'distance': reportsummary['distance'],
                    'averageSpeed': reportsummary['averageSpeed'],
                    'maxSpeed': reportsummary['maxSpeed'],
                    'spentFuel': reportsummary['spentFuel'],
                    'startOdometer': reportsummary['startOdometer'],
                    'endOdometer': reportsummary['endOdometer'],
                    'startPositionId': reportsummary['startPositionId'],
                    'endPositionId': reportsummary['endPositionId'],
                    'startLat': reportsummary['startLat'],
                    'startLon': reportsummary['startLon'],
                    'endLat': reportsummary['endLat'],
                    'endLon': reportsummary['endLon'],
                    'startTime': reportsummary['startTime'],
                    'startAddress': reportsummary['startAddress'],
                    'endTime': reportsummary['endTime'],
                    'endAddress': reportsummary['endAddress'],
                    'duration': reportsummary['duration']
                })
    return final_values


def get_last_position(cookie, device_id):
    params = {'uniqueID': device_id, 'from': '2000-01-01T00:00:00.000Z', 'to': '2050-01-01T00:00:00.000Z'}
    headers = {'Cookie': cookie[0], 'Content-Type': 'application/json', 'Accept': 'application/json'}
    response = requests.get(cookie[1] + '/api/positions', headers=headers, params=params)
    result = 0, 0, None, None
    for position in response.json():
        if position['deviceId'] == device_id:
            totalDistance = 0
            if 'attributes' in position and position['attributes'].get('totalDistance', False): totalDistance = \
                position['attributes'].get('totalDistance', 0)
            result = float(position['latitude']), float(position['longitude']), datetime.datetime.strptime(
                position['fixTime'], '%Y-%m-%dT%H:%M:%S.000+0000'), totalDistance
    return result


class FleetVehicleLastLocation(models.TransientModel):
    _name = "fleet.vehicle.last.location"
    _description = 'Vehicle Last Location on the Map'

    @api.depends('vehicle_id')
    def _compute_bokeh_chart(self):
        for rec in self:
            map_options = GMapOptions(lat=rec.vehicle_id.vehicle_latitude or 0,
                                      lng=rec.vehicle_id.vehicle_longitude or 0, map_type="roadmap",
                                      zoom=11)

            # For GMaps to function, Google requires you obtain and enable an API key:
            #     https://developers.google.com/maps/documentation/javascript/get-api-key
            gmaps_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
            if not gmaps_api_key:
                raise UserError(
                    _("You have not entered a Google Maps API key (under Fleet - Traccar Settings), please do so to view map views."))
            p = gmap(gmaps_api_key, map_options, title="Last Map Location")

            source = ColumnDataSource(
                data=dict(lat=[rec.vehicle_id.vehicle_latitude or 0],
                          lon=[rec.vehicle_id.vehicle_longitude or 0])
            )

            p.circle(x="lon", y="lat", size=15, fill_color="blue", fill_alpha=0.8, source=source)
            p.add_tools(SaveTool())
            # p.sizing_mode = 'scale_width'

            # Get the html components and convert them to string into the field.
            script, div = components(p)
            rec.bokeh_last_location = '%s%s' % (div, script)

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    bokeh_last_location = fields.Text(
        string='Trip',
        compute=_compute_bokeh_chart, track_visibility='always')


class FleetVehicleTripHistory(models.Model):
    _name = "fleet.vehicle.trip.history"

    @api.depends('duration')
    def show_hr_mm(self):
        for record in self:
            if record.duration != 0:
                record.display_engine_hours = convert_hr_mm(record.duration)

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    distance = fields.Float(string='Distance', digits=(16, 5))
    duration = fields.Integer(string="Duration")
    end_address = fields.Char(string="End Address")
    end_lat = fields.Float(string="End Lat", digits=(16, 5))
    end_lon = fields.Float(string="End Lon", digits=(16, 5))
    end_time = fields.Datetime(string="End Time")
    max_speed = fields.Float(string="Max speed", digits=(16, 5))
    avg_speed = fields.Float(string="Avg speed", digits=(16, 5))
    spent_fuel = fields.Float(string="Spent Fuel", digits=(16, 5))
    start_address = fields.Char(string="Start Address")
    start_lat = fields.Float(string="Start Lat", digits=(16, 5))
    start_lon = fields.Float(string="Start Lon", digits=(16, 5))
    start_time = fields.Datetime(string="Start Time")
    start_odometer = fields.Float(string="Start Mileage", digits=(16, 5))
    end_odometer = fields.Float(string="End Mileage", digits=(16, 5))
    average_speed = fields.Float(string="Average Speed (KM/H)", digits=(16, 5))
    start_mileage = fields.Float(string="Start Mileage", digits=(16, 5))
    end_mileage = fields.Float(string="End Mileage", digits=(16, 5))

class FleetVehicleLocationHistory(models.Model):
    _name = "fleet.vehicle.location.history"
    _order = 'date_localization desc'
    _description = 'Vehicle Location History'

    def _compute_inactive(self):
        for rec in self:
            rec.inactive_period = False
            if not rec.vehicle_id or (
                    rec.vehicle_latitude == 0 and rec.vehicle_longitude == 0) or not rec.date_localization:
                continue

            ir_config_param = self.env['ir.config_parameter'].sudo()
            inactivity_period_duration = ir_config_param.get_param('inactivity_period_duration', default='30')
            on_date = rec.date_localization
            date_localization_from = on_date - datetime.timedelta(minutes=int(inactivity_period_duration))

            all_history_records = self.search(
                [('vehicle_id', '=', rec.vehicle_id.id), ('date_localization', '>=', date_localization_from),
                 ('date_localization', '<=', rec.date_localization)])
            if all_history_records:
                inactive = False
                for h in all_history_records:
                    if round(h.vehicle_latitude, 4) != round(rec.vehicle_latitude, 4) or round(h.vehicle_longitude,
                                                                                               4) != round(
                        rec.vehicle_longitude, 4):  # if locations are close enough
                        inactive = False
                        break
                    else:
                        inactive = True
                if inactive: rec.inactive_period = True

    @api.depends('date_localization')
    def _compute_bokeh_chart(self):
        for rec in self:
            on_date = self.date_localization
            day_after = on_date + datetime.timedelta(days=1)

            day_points = self.env['fleet.vehicle.location.history'].search([('vehicle_id', '=', self.vehicle_id.id),
                                                                            ('date_localization', '<', day_after),
                                                                            ('date_localization', '>=', on_date)])
            if not day_points:
                # no data
                return

            data = {
                'lat': [],
                'lon': [],
                'info': []
            }
            for point in day_points:
                data['lat'].append(point.vehicle_latitude)
                data['lon'].append(point.vehicle_longitude)
                data['info'].append(point.driver_name + ' - ' + point.date_localization.strftime("%Y-%m-%d %H:%M:%S"))

            map_options = GMapOptions(lat=rec.vehicle_latitude,
                                      lng=rec.vehicle_longitude, map_type="roadmap", zoom=11)

            gmaps_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
            if not gmaps_api_key:
                raise UserError(_(
                    "You have not entered a Google Maps API key (under Fleet - Traccar Settings), please do so to view map views."))
            p = GMapPlot(api_key=gmaps_api_key, x_range=Range1d(),
                         y_range=Range1d(), map_options=map_options)  # , title="My Drive")

            source = ColumnDataSource(data=dict(lat=data['lat'], lon=data['lon'],
                                                info=data['info'], ))

            path = Line(x="lon", y="lat", line_width=3, line_color='blue', line_alpha=0.8)
            car = Circle(x="lon", y="lat", size=10, fill_color='red', fill_alpha=0.9)

            # p = figure(title="PNG Highlands Earthquake 7.5 Affected Villages", y_range=(-4.31509, -7.0341),
            #           x_range=(141.26667, 145.56598))
            # p.xaxis.axis_label = 'longitude'
            # p.yaxis.axis_label = 'latitude'

            p.add_glyph(source, path)
            source = ColumnDataSource(data=dict(lat=[rec.vehicle_latitude], lon=[rec.vehicle_longitude],
                                                info=[rec.driver_name + ' - ' + rec.date_localization.strftime(
                                                    "%Y-%m-%d %H:%M:%S")]))
            p.add_glyph(source, car)
            p.add_tools(PanTool(), WheelZoomTool(), SaveTool(),
                        HoverTool(tooltips=[("Info", "@info"), ]))
            p.sizing_mode = 'scale_width'
            p.toolbar.active_scroll = "auto"

            script, div = components(p)
            rec.trip = '%s%s' % (div, script)
            rec.on_date = on_date.date()

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    name = fields.Char(string='Name', required=True)
    driver_name = fields.Char(string='Driver Name')
    image_128 = fields.Binary(related='vehicle_id.image_128', string="Logo (small)")
    vehicle_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    vehicle_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    date_localization = fields.Datetime(string='Located on')
    inactive_period = fields.Boolean(string='Inactive Period', compute='_compute_inactive', store=False)

    on_date = fields.Date(string='On Date', compute=_compute_bokeh_chart)
    all_day = fields.Boolean(string='All Day', default=True)
    trip = fields.Text(
        string='Trip',
        compute=_compute_bokeh_chart)


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"
    display_engine_hours = fields.Char(string="Engine Hours", compute="show_hr_mm")
    current_speed = fields.Float(string="Current Speed (km/h)")
    average_speed = fields.Float(string='Average Speed (km/h)')
    max_speed = fields.Float(string='Max Speed (km/h)')
    latest_speed_datetime = fields.Datetime(string='Last Update DT', index=True, )
    device_status = fields.Selection(selection=[
        ('online', 'Online'),
        ('offline', 'Offline'),
    ], string='Device Status', copy=False,
        default='offline')
    license_expired_date = fields.Date(string="License Expire Date")

    @api.onchange('traccar_uniqueID')
    def get_device_status(self):
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')
        url = "https://hk-open.tracksolidpro.com/route/rest"
        #url = "http://open.10000track.com/route/rest"
        #cookie = self.login()
        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
        }
        app_key = self.env['ir.config_parameter'].sudo().get_param('app_key')
        app_key = app_key if app_key else '8FB345B8693CCD00AC3E48A9D2EABBA6'

        if self.traccar_uniqueID:
            #token = self.get_tracksolid_token()
            token = self.get_tracksolid_token_parameter()
            if token == "error":
                raise ValidationError(
                    _("Vehicle  API Error and please check with GPS Vendor.ERROR:'Request frequency is too high today!'"))
            else:
                traccar_device_id = self.traccar_uniqueID
                ir_config_obj = self.env['ir.config_parameter'].sudo()
                utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if traccar_device_id: #cookie and traccar_device_id:
                    from_date = datetime.utcnow().strftime('%Y-%m-%d 00:00:00')
                    to_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    body = {'method': "jimi.device.location.get",
                            'timestamp': utc_current,
                            'app_key': app_key,
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",
                            'imeis': traccar_device_id,
                            'app_key': app_key,
                            'expires_in': 900
                            }
                    self.latest_speed_datetime = fields.Datetime.now()
                    response = requests.request("POST", url, headers={}, params=body)
                    if response.status_code == 200:
                        res_data = json.loads(response.content.decode('utf-8'))
                        results = res_data['result']
                        self.device_status = 'offline'
                        if results and 'speed' in results:
                            self.current_speed = results['speed']
                            if self.current_speed > 0 and self.max_speed == 0 and self.current_speed > self.max_speed:
                                self.max_speed = self.current_speed
                            self.device_status = 'online'
                        else:
                            erro_msg = "Vehicle  IMEI  %s is offline.to check speeds.!" % traccar_device_id
                            _logger.info(erro_msg)
                    else:
                        token = self.get_tracksolid_token()
                        if token == "error":
                            raise ValidationError(
                                _("Vehicle  API Error and please check with GPS Vendor.ERROR: 'Request frequency is too high today!''"))
                        from_date = datetime.utcnow().strftime('%Y-%m-%d 00:00:00')
                        to_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                        body = {'method': "jimi.device.location.get",
                                'timestamp': utc_current,
                                'app_key': app_key,
                                'access_token': token['accessToken'],
                                'v': "0.9",
                                'sign_method': "md5",
                                'format': "json",
                                'imeis': traccar_device_id,
                                'app_key': app_key,
                                'expires_in': 900
                                }
                        self.latest_speed_datetime = fields.Datetime.now()
                        response = requests.request("POST", url, headers={}, params=body)
                        if response.status_code == 200:
                            res_data = json.loads(response.content.decode('utf-8'))
                            results = res_data['result']
                            self.device_status = 'offline'
                            if results and 'speed' in results:
                                self.current_speed = results['speed']
                                if self.current_speed > 0 and self.max_speed == 0 and self.current_speed > self.max_speed:
                                    self.max_speed = self.current_speed
                                self.device_status = 'online'
                            else:
                                erro_msg = "Vehicle  IMEI  %s is offline.to check speeds.!" % traccar_device_id
                                _logger.info(erro_msg)

    def get_device_avg_speed(self):
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')
        url = "https://hk-open.tracksolidpro.com/route/rest"
        #url = "http://open.10000track.com/route/rest"
        #cookie = self.login()
        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
        }
        app_key = self.env['ir.config_parameter'].sudo().get_param('app_key')
        app_key = app_key if app_key else '8FB345B8693CCD00AC3E48A9D2EABBA6'
        average_speed = 0
        tz_name = self.env.context.get('tz') or self.env.user.tz
        if self.traccar_uniqueID:
            #token = self.get_tracksolid_token()
            token = self.get_tracksolid_token_parameter()
            if token != "error":
                traccar_device_id = self.traccar_uniqueID
                ir_config_obj = self.env['ir.config_parameter'].sudo()
                current_utc = datetime.now()
                ygn = pytz.timezone('Asia/Yangon')
                now_time = current_utc.astimezone(ygn)
                # from_date = now_time.strftime('%Y-%m-%d 00:00:00')
                from_date = '2021-08-01 00:00:00'
                to_date = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)#self.convert_TZ_UTC(datetime.now())
                #to_date = utc_current.strftime('%Y-%m-%d %H:%M:%S')
                print("now : ", now_time)
                print("from date : ", from_date)
                print("to date : ", to_date)
                utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                #utc_current = self.convert_TZ_UTC(datetime.now())
                if traccar_device_id:#cookie and traccar_device_id:
                    body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': app_key,
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",
                            'imeis': traccar_device_id,
                            'app_key': app_key,
                            'begin_time': from_date,
                            'end_time': to_date,
                            'expires_in': 900
                            }
                    response = requests.request("POST", url, headers=headers, params=body)
                    self.create_api_log("get_device_avg_speed", body, response.status_code, response.text)
                    if response.status_code == 200:
                        res_data = json.loads(response.content.decode('utf-8'))
                        if not 'result' in res_data:
                            return False
                        results = res_data['result']
                        print("res data : ", res_data)
                        print("result : ", results)
                        if results:
                            avg_speed = results[0]
                            if 'avgSpeed' in avg_speed:
                                average_speed = avg_speed['avgSpeed']
                    else:
                        token = self.get_tracksolid_token_parameter()
                        body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': app_key,
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",
                            'imeis': traccar_device_id,
                            'app_key': app_key,
                            'begin_time': from_date,
                            'end_time': to_date,
                            'expires_in': 900
                            }
                        response = requests.request("POST", url, headers=headers, params=body)
                        self.create_api_log("get_device_avg_speed", body, response.status_code, response.text)
                        if response.status_code == 200:
                            res_data = json.loads(response.content.decode('utf-8'))
                            results = res_data['result']
                            print("res data : ", res_data)
                            print("result : ", results)
                            if results:
                                avg_speed = results[0]
                                if 'avgSpeed' in avg_speed:
                                    average_speed = avg_speed['avgSpeed']

        return average_speed
    def get_device_odometer(self):

        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')
        url = "https://hk-open.tracksolidpro.com/route/rest"
        # url = "http://open.10000track.com/route/rest"
        # cookie = self.login()
        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
        }

        if self.traccar_uniqueID:
            # for vehicle in self.env['fleet.vehicle'].search([('id', 'in', [1602,1603])]):
            # token = self.get_tracksolid_token()
            token = self.get_tracksolid_token_parameter()
            if token != "error":
                traccar_device_id = self.traccar_uniqueID
                ir_config_obj = self.env['ir.config_parameter'].sudo()

                # utc_current = self.convert_TZ_UTC(datetime.now())
                utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if traccar_device_id:  # cookie and traccar_device_id:
                    if self.last_odometer_datetime:
                        from_date = self.last_odometer_datetime  # vehicle.last_odometer_datetime.strftime("%Y-%M-%d %H:%M:%S")
                    else:
                        from_date = '2019-09-01 00:00:00'
                    # for rec in self.env['fleet.vehicle.trip.history'].search([('vehicle_id', '=', vehicle.id)],
                    #                                                          order="end_time desc", limit=1):
                    #     a_date = rec.end_time or ''
                    #     tmp_date = rec.end_time #.strftime("%Y-%M-%d %H:%M:%S")
                    #     from_date = tmp_date

                    to_date = utc_current
                    body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': '8FB345B8693CCD00AC3E48A9D2EABBA6',
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",

                            'imeis': traccar_device_id,
                            'begin_time': from_date,  # 1603757920,
                            'end_time': to_date,  # 1603793920
                            'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                            'expires_in': 900
                            }
                    results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                    response = requests.request("POST", url, headers={}, params=body)

                    print(response.status_code)
                    if response.status_code == 200:
                        res_data = json.loads(response.content.decode('utf-8'))
                        print(res_data)
                        if not 'result' in res_data:
                            return True
                        results = res_data['result']
                        if results is None:
                            return True
                        pprint(results)
                        for result in results:

                            res = {
                                'vehicle_id': self.id,
                                'duration': result['runTimeSecond'],
                                'distance': float(result['distance']) / 1000,
                                'avg_speed': result['avgSpeed'],
                                # 'max_speed':result['maxSpeed'],
                                # 'spent_fuel': result['spentFuel'],
                                # 'start_address': result['startAddress'],
                                'start_lat': result['startLat'],
                                'start_lon': result['startLng'],
                                'start_time': result['startTime'],
                                # 'end_address': result['endAddress'],
                                'end_lat': result['endLat'],
                                'end_lon': result['endLng'],
                                'end_time': result['endTime'],
                                'start_odometer': result['startMileage'],
                                'end_odometer': result['endMileage'],
                                'start_mileage': result['startMileage'],
                                'end_mileage': result['endMileage'],
                                # 'startPositionId': result['startPositionId'],
                                # 'endPositionId': result['endPositionId'],

                            }
                            trip_id = self.env['fleet.vehicle.trip.history'].search(
                                [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                                 ('vehicle_id', '=', self.id)])
                            if trip_id:
                                trip_id.write(res)
                            else:
                                self.env['fleet.vehicle.trip.history'].create(res)
                    else:
                        token = self.get_tracksolid_token()
                        to_date = utc_current
                        body = {'method': "jimi.device.track.mileage",
                                'timestamp': utc_current,
                                'app_key': '8FB345B8693CCD00AC3E48A9D2EABBA6',
                                'access_token': token['accessToken'],
                                'v': "0.9",
                                'sign_method': "md5",
                                'format': "json",

                                'imeis': traccar_device_id,
                                'begin_time': from_date,  # 1603757920,
                                'end_time': to_date,  # 1603793920
                                'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                                'expires_in': 900
                                }
                        results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                        response = requests.request("POST", url, headers={}, params=body)

                        print(response.status_code)
                        if response.status_code == 200:
                            res_data = json.loads(response.content.decode('utf-8'))
                            if not 'result' in res_data:
                                return True
                            results = res_data['result']
                            if results is None:
                                return True
                            pprint(results)
                            for result in results:

                                res = {
                                    'vehicle_id': self.id,
                                    'duration': result['runTimeSecond'],
                                    'distance': float(result['distance']) / 1000,
                                    'avg_speed': result['avgSpeed'],
                                    # 'max_speed':result['maxSpeed'],
                                    # 'spent_fuel': result['spentFuel'],
                                    # 'start_address': result['startAddress'],
                                    'start_lat': result['startLat'],
                                    'start_lon': result['startLng'],
                                    'start_time': result['startTime'],
                                    # 'end_address': result['endAddress'],
                                    'end_lat': result['endLat'],
                                    'end_lon': result['endLng'],
                                    'end_time': result['endTime'],
                                    'start_odometer': result['startMileage'],
                                    'end_odometer': result['endMileage'],
                                    'start_mileage': result['startMileage'],
                                    'end_mileage': result['endMileage'],
                                    # 'startPositionId': result['startPositionId'],
                                    # 'endPositionId': result['endPositionId'],

                                }
                                trip_id = self.env['fleet.vehicle.trip.history'].search(
                                    [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                                     ('vehicle_id', '=', self.id)])
                                if trip_id:
                                    trip_id.write(res)
                                else:
                                    self.env['fleet.vehicle.trip.history'].create(res)
            _logger.info("update_trip_odometer vehicle>>>>>>: %s fromdate >>>>>>>>>>> %s" % (self.id, from_date))
            odometer = self.update_trip_odometer(self, from_date)
        return True

    def get_device_odometer_old(self):
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')
        url = "https://hk-open.tracksolidpro.com/route/rest"
        #url = "http://open.10000track.com/route/rest"
        #cookie = self.login()
        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
        }
        app_key = self.env['ir.config_parameter'].sudo().get_param('app_key')
        app_key = app_key if app_key else '8FB345B8693CCD00AC3E48A9D2EABBA6'
        current_odemeter = 0
        tz_name = self.env.context.get('tz') or self.env.user.tz
        if self.traccar_uniqueID:
            #token = self.get_tracksolid_token()
            token = self.get_tracksolid_token_parameter()
            print(token)
            if token != "error":
                traccar_device_id = self.traccar_uniqueID
                ir_config_obj = self.env['ir.config_parameter'].sudo()
                current_utc = datetime.now()
                ygn = pytz.timezone('Asia/Yangon')
                now_time = current_utc.astimezone(ygn)                
                # from_date = now_time.strftime('%Y-%m-%d 00:00:00')
                if self.last_odometer_datetime:
                    from_date = self.last_odometer_datetime  # vehicle.last_odometer_datetime.strftime("%Y-%M-%d %H:%M:%S")
                else:
                    from_date = '2021-08-01 00:00:00'

                to_date = now_time.strftime('%Y-%m-%d %H:%M:%S')
                #to_date = self.convert_TZ_UTC(datetime.now())
                print("now : ", now_time)
                print("from date : ", from_date)
                print("to date : ", to_date)
                utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                #utc_current = self.convert_TZ_UTC(datetime.now())
                if traccar_device_id:#cookie and traccar_device_id:
                    body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': app_key,
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",
                            'imeis': traccar_device_id,
                            'app_key': app_key,
                            'begin_time': from_date,
                            'end_time': to_date,
                            'expires_in': 900
                            }
                    response = requests.request("POST", url, headers=headers, params=body)
                    if response.status_code == 200:
                        res_data = json.loads(response.content.decode('utf-8'))
                        if not 'result' in res_data:
                            return current_odemeter
                        #if res_data['result']:
                        results = res_data['result']
                        print("res data : ", res_data)
                        print("result : ", results)
                        if results:
                            last_mile = results[0]
                            if 'endMileage' in last_mile:
                                current_odemeter = round(last_mile['endMileage'] / 1000, 0)
                    else:
                        token = self.get_tracksolid_token()
                        body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': app_key,
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",
                            'imeis': traccar_device_id,
                            'app_key': app_key,
                            'begin_time': from_date,
                            'end_time': to_date,
                            'expires_in': 900
                            }
                        response = requests.request("POST", url, headers=headers, params=body)
                        if response.status_code == 200:
                            res_data = json.loads(response.content.decode('utf-8'))
                            if not 'result' in res_data:
                                return current_odemeter
                            results = res_data['result']
                            print("res data : ", res_data)
                            print("result : ", results)
                            if results:
                                last_mile = results[0]
                                print("last mile>>>",last_mile)
                                if 'endMileage' in last_mile:
                                    current_odemeter = round(last_mile['endMileage'] / 1000, 0)
        return current_odemeter

    def convert_withtimezone(self, userdate):
        """ 
        Convert to Time-Zone with compare to UTC
        """
        user_date = datetime.strptime(userdate, DEFAULT_SERVER_DATETIME_FORMAT)
        tz_name = self.env.context.get('tz') or self.env.user.tz
        if tz_name:
            utc = pytz.timezone('UTC')
            context_tz = pytz.timezone(tz_name)
            # not need if you give default datetime into entry ;)
            user_datetime = user_date  # + relativedelta(hours=24.0)
            local_timestamp = context_tz.localize(user_datetime, is_dst=False)
            user_datetime = local_timestamp.astimezone(utc)
            return user_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return user_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _get_engine_on_off(self):
        FleetVehicleTrip = self.env['fleet.vehicle.trip.history']
        for record in self:
            trips = FleetVehicleTrip.search([('vehicle_id', '=', record.id)], order='start_time desc', limit=1)
            # t_start_date = datetime.strftime(trips.start_time.strftime("%Y-%m-%d"), "%Y-%m-%d")#self.convert_withtimezone(trips.start_time+' 00:00:00')
            record.morning_engine_on = False
            record.last_engine_off = False
            for trip in trips:
                t_start_date = trip.start_time.date()
                # datetime = time.strftime('%A, %Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                start_date = str(t_start_date) + ' 00:00:00'
                end_date = str(t_start_date) + ' 23:59:59'
                for early in FleetVehicleTrip.search([('vehicle_id', '=', record.id), ('start_time', '>=', start_date),
                                                      ('end_time', '<=', end_date)], order='start_time asc', limit=1):
                    record.morning_engine_on = early.start_time
                for last in FleetVehicleTrip.search([('vehicle_id', '=', record.id), ('start_time', '>=', start_date),
                                                     ('end_time', '<=', end_date)], order='end_time desc', limit=1):
                    record.last_engine_off = last.start_time

    def _get_engine_hr(self):
        FleetVehicleTrip = self.env['fleet.vehicle.trip.history']
        for record in self:
            trips = FleetVehicleTrip.search([('vehicle_id', '=', record.id)], order='start_time asc')
            record.engine_hours = 0
            for trip in trips:
                record.engine_hours += trip.duration

    def _compute_bokeh_chart(self):
        for rec in self:
            map_options = GMapOptions(lat=rec.vehicle_latitude or 0, lng=rec.vehicle_longitude or 0, map_type="roadmap",
                                      zoom=11)

            # For GMaps to function, Google requires you obtain and enable an API key:
            #     https://developers.google.com/maps/documentation/javascript/get-api-key
            gmaps_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
            if not gmaps_api_key:
                raise UserError(
                    _("You have not entered a Google Maps API key (under Fleet - Traccar Settings), please do so to view map views."))
            p = gmap(gmaps_api_key, map_options, title="Last Map Location")

            source = ColumnDataSource(
                data=dict(lat=[rec.vehicle_latitude or 0],
                          lon=[rec.vehicle_longitude or 0])
            )

            p.circle(x="lon", y="lat", size=15, fill_color="blue", fill_alpha=0.8, source=source)
            p.add_tools(PanTool(), WheelZoomTool(), SaveTool())
            p.sizing_mode = 'scale_width'

            # Get the html components and convert them to string into the field.
            script, div = components(p)
            rec.bokeh_last_location = '%s%s' % (div, script)

    def _reverse_geocode(self):
        ir_config_param = self.env['ir.config_parameter'].sudo()
        do_reverse_geocoding = ir_config_param.get_param('do_reverse_geocoding') or False
        if do_reverse_geocoding:
            for record in self:
                record.current_address = ''
                result = ''
                base = "https://maps.googleapis.com/maps/api/geocode/json?"
                gmaps_api_key = ir_config_param.get_param('google.api_key_geocode') or ''
                params = "latlng={lat},{lon}&sensor={sen}&key={key}".format(
                    lat=record.vehicle_latitude,
                    lon=record.vehicle_longitude,
                    sen='false',
                    key=gmaps_api_key
                )
                url = "{base}{params}".format(base=base, params=params)
                try:
                    response = requests.get(url)
                    res_json = response.json() if response else False
                    if res_json.get('status') != 'OK':
                        continue
                    result = res_json and res_json.get('results', False) and res_json.get('results')[0][
                        'formatted_address'] or ''
                except Exception as e:
                    _logger.exception(_(
                        'Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)
                if result: record.current_address = result

    def change_hr_mm(self):
        for record in self:
            record.display_engine_hours = 0
            if record.engine_hours != 0:
                record.display_engine_hours = convert_hr_mm(record.engine_hours)

    def change_color_on_kanban(self):
        """    this method is used to change color index :return: index of color for kanban view    """
        for record in self:
            active_time = None
            if record.date_localization:
                inactivity_period_duration = self.env['ir.config_parameter'].sudo().get_param(
                    'inactivity_period_duration', default='30')
                active_time = fields.Datetime.datetime.datetime.now() - datetime.timedelta(
                    minutes=int(inactivity_period_duration))
            if record.gps_tracking and record.vehicle_latitude and record.vehicle_longitude and record.date_localization >= active_time:
                color = 5
                state = 'Tracking'
            elif record.gps_tracking:
                color = 7
                state = 'Tracking, not active'
            elif not record.gps_tracking:
                color = 2
                state = 'Not tracking'
            else:
                color = 0
                state = 'Unknown'
            record.kanban_color = color
            record.kanban_state = state

    vehicle_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    vehicle_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    current_address = fields.Char(string='Current Address', compute='_reverse_geocode', store=False)
    date_localization = fields.Datetime(string='Last Time Geolocated')
    traccar_uniqueID = fields.Char(string='Traccar unique ID')
    traccar_device_id = fields.Integer(string='Traccar device ID')
    gps_tracking = fields.Boolean(string='Tracking')
    location_history_ids = fields.One2many('fleet.vehicle.location.history', 'vehicle_id', string='Location History',
                                           copy=False, readonly=True)

    working_hours_from = fields.Float(string='Shift Starting Hour')
    working_hours_to = fields.Float(string='Shift Ending Hour')
    date_inactive_filter = fields.Date(string='On Date', store=False)

    pre_tracking_odometer = fields.Float(string='Odometer Before Tracking Started',
                                         help='Odometer status when the vehicle was started to be tracked on (each location update then updates the odometer).')

    bokeh_last_location = fields.Text(
        string='Last Location',
        compute=_compute_bokeh_chart)
    kanban_color = fields.Integer('Color Index', compute="change_color_on_kanban")
    kanban_state = fields.Char('Tracking State', compute="change_color_on_kanban")
    maxs_peed = fields.Float(string='Max Speed')
    spent_fuel = fields.Float(string='Spent Fuel')
    engine_hours = fields.Integer(compute='_get_engine_hr', string="Engine Hours(milliseconds)")
    morning_engine_on = fields.Datetime(compute='_get_engine_on_off', string="Morning Engine On")
    last_engine_off = fields.Datetime(compute='_get_engine_on_off', string="Last Engine Off")
    display_engine_hours = fields.Char(string="Engine Hours", compute="change_hr_mm")
    trip_history_ids = fields.One2many('fleet.vehicle.trip.history', 'vehicle_id', string='Trip History', copy=False,
                                       readonly=True)

    def return_action_to_open_trip(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('traccar_fleet_tracking', xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    def action_show_daytrip(self):
        self.ensure_one()
        context = self.env.context.copy()
        context['default_vehicle_id'] = self.id
        new_ids = []
        all_dates = []
        all_location_records = self.env['fleet.vehicle.location.history'].search(
            [('vehicle_id', '=', self.id), ('date_localization', '!=', False), ('vehicle_latitude', '!=', 0),
             ('vehicle_longitude', '!=', 0)], order='date_localization desc')
        if all_location_records:
            for day in all_location_records:
                last_date = day.date_localization.date()
                if last_date not in all_dates:
                    all_dates.append(last_date)
                    new_id = self.env['fleet.vehicle.day.trip'].create({'vehicle_id': self.id, 'on_date': last_date})
                    if new_id:
                        new_ids.append(new_id.id)
        view_id = self.env.ref('traccar_fleet_tracking.view_vehicle_day_trip_calendar')
        return {
            'name': _('Daily Trip Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle.day.trip',
            'view_mode': 'calendar',
            'view_type': 'calendar',
            'target': 'current',
            'views': [(view_id.id, 'calendar')],
            'context': context,
            'domain': [('id', 'in', new_ids)]
        }

    def action_show_last_map_location(self):
        self.ensure_one()
        context = self.env.context.copy()
        context['default_vehicle_id'] = self.id
        new_id = self.env['fleet.vehicle.last.location'].create({'vehicle_id': self.id})
        view_id = self.env.ref('traccar_fleet_tracking.view_vehicle_last_location')
        return {
            'name': _('Last Location on the Map'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle.last.location',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'view_id': view_id and view_id.id or False,
            'context': context,
            'domain': [('id', 'in', [new_id and new_id.id or False])]
        }

    def action_show_map(self):
        self.ensure_one()
        context = self.env.context.copy()
        vehicles = [self.id]
        view_map_id = self.env.ref('traccar_fleet_tracking.view_fleet_vehicle_map')
        return {
            'name': _('Map'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'view_mode': 'map',
            'view_type': 'map',
            'views': [(view_map_id.id, 'map')],
            'context': context,
            'domain': [('id', 'in', vehicles)]
        }

    def toggle_gps_tracking(self):
        """ Inverse the value of the field ``gps_tracking`` on the records in ``self``. """
        for record in self:
            if not record.traccar_uniqueID:
                raise exceptions.Warning(
                    _('You have not provided a Traccar device unique ID, please click Edit and enter it before adding/removing a device!'))
            record.gps_tracking = not record.gps_tracking

            try:
                cookie = record.login()
                uniqueID = record.traccar_uniqueID
                if record.gps_tracking:
                    record.add_device(cookie, uniqueID)
                else:
                    record.remove_device(cookie, uniqueID)
            except:
                raise exceptions.Warning(_("Could not connect to Traccar, please check your Traccar Settings!"))

    def login(self):
        ir_config_obj = self.env['ir.config_parameter'].sudo()
        url = ir_config_obj.get_param('traccar_server_url', default='http://127.0.0.1:8082')
        traccar_username = ir_config_obj.get_param('traccar_username', default='admin')
        traccar_password = ir_config_obj.get_param('traccar_password', default='admin')

        response = requests.post(url + '/api/session', data={'email': traccar_username, 'password': traccar_password})
        res = response.headers.get('Set-Cookie'), url

        # check if there's an Odoo group in Traccar, which we link all the devices from Odoo and all geofences to
        self.check_odoo_traccar_group(res)

        return res

    def check_odoo_traccar_group(self, cookie):
        ir_config_obj = self.env['ir.config_parameter'].sudo()
        headers = {'Cookie': cookie[0], 'Content-Type': 'application/json', 'Accept': 'application/json'}
        group_id = False
        OdooTraccarGroupId = ir_config_obj.get_param('odoo_traccar_groupId')
        try:
            if OdooTraccarGroupId:
                response = requests.get(cookie[1] + '/api/groups', headers=headers)
                data = response.json()
                group_id = False
                for group in data:
                    if str(OdooTraccarGroupId) == str(group['id']):
                        group_id = True
            if not group_id:
                group = {'name': 'Odoo Group'}
                response = requests.post(cookie[1] + '/api/groups', headers=headers, data=json.dumps(group))
                data = response.json()
                group_id = data and data['id'] or False
                if group_id:
                    ir_config_obj.set_param('odoo_traccar_groupId', (group_id))
        except:
            _logger.exception("Traccar - Odoo group retrieval failed.")

    def remove_device(self, cookie, uniqueID):
        headers = {'Cookie': cookie[0], 'Content-Type': 'application/json', 'Accept': 'application/json'}
        response = requests.get(cookie[1] + '/api/devices', headers=headers)
        data = response.json()
        for device in data:
            if uniqueID == device['uniqueId']:
                response = requests.delete(cookie[1] + '/api/devices/' + str(device['id']), headers=headers)

    def add_device(self, cookie, uniqueID):
        headers = {'Cookie': cookie[0], 'Content-Type': 'application/json', 'Accept': 'application/json'}
        response = requests.get(cookie[1] + '/api/devices', headers=headers)
        data = response.json()
        device_id = False
        for device in data:
            if uniqueID == device['uniqueId']:
                device_id = device['id']

        if not device_id:
            OdooTraccarGroupId = self.env['ir.config_parameter'].sudo().get_param('odoo_traccar_groupId')
            device = {'name': self.name, 'uniqueId': uniqueID}
            if OdooTraccarGroupId: device.update(groupId=OdooTraccarGroupId)
            response = requests.post(cookie[1] + '/api/devices', headers=headers, data=json.dumps(device))
            data = response.json()
            device_id = data and data['id'] or False
        self.write({'traccar_device_id': device_id})

    def get_trip(self):
        add_to_odometer = True if self.env['ir.config_parameter'].sudo().get_param('add_to_odometer',
                                                                                   'False').lower() != 'false' else False
        # get superuser's timezone
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')

        #cookie = self.login()
        for vehicle in self:
            traccar_device_id = vehicle.traccar_device_id
            ir_config_obj = self.env['ir.config_parameter'].sudo()
            OdooTraccarGroupId = ir_config_obj.get_param('odoo_traccar_groupId') or False
            if traccar_device_id: #cookie and traccar_device_id:
                from_date = '2019-09-01T00:00:00.000Z'
                for rec in self.env['fleet.vehicle.trip.history'].search([('vehicle_id', '=', vehicle.id)],
                                                                         order="end_time desc", limit=1):
                    a_date = rec.end_time or ''
                    tmp_date = rec.end_time.strftime("%Y-%M-%d %H:%M:%S")
                    # tmp_date = datetime.datetime.strptime(rec.end_time,'%Y-%M-%d %H:%M:%S')
                    # date = datetime.strptime('Thu, 16 Dec 2010 12:14:05', '%a, %d %b %Y %H:%M:%S')
                    from_date = a_date.isoformat(sep='T', timespec='milliseconds')
                    from_date += 'Z'
                    # from_date = rec.end_time.isoformat()
                to_date = datetime.datetime.now().isoformat(sep='T', timespec='milliseconds')
                to_date += 'Z'
                results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                for result in results:
                    if result.get('duration'):
                        # fixTime = tz.localize(result['startTime'])
                        # fixTime = fixTime.astimezone(pytz.utc)

                        res = {
                            'vehicle_id': vehicle.id,
                            'duration': result['duration'],
                            'distance': result['distance'],
                            'avg_speed': result['averageSpeed'],
                            'max_speed': result['maxSpeed'],
                            'spent_fuel': result['spentFuel'],
                            'start_address': result['startAddress'],
                            'start_lat': result['startLat'],
                            'start_lon': result['startLon'],
                            'start_time': result['startTime'],
                            'end_address': result['endAddress'],
                            'end_lat': result['endLat'],
                            'end_lon': result['endLon'],
                            'end_time': result['endTime'],
                            'start_odometer': result['startOdometer'],
                            'end_odometer': result['endOdometer'],
                            # 'startPositionId': result['startPositionId'],
                            # 'endPositionId': result['endPositionId'],

                        }
                        trip_id = self.env['fleet.vehicle.trip.history'].search(
                            [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                             ('vehicle_id', '=', vehicle.id)])
                        if trip_id:
                            trip_id.write(res)
                        else:
                            self.env['fleet.vehicle.trip.history'].create(res)

        return True
    
    def update_trip_odometer(self,vehicle,from_date):
        trip_odometer = 0
        for rec in self.env['fleet.vehicle.trip.history'].search([('vehicle_id', '=', vehicle.id),('start_time','>=',from_date)],
                                                                             order="end_time desc"):
            end_mileage = rec.end_mileage - rec.start_mileage
            if end_mileage > 0:
                trip_odometer +=  end_mileage / 1000#1.60934
        
        trip_id = self.env['fleet.vehicle.trip.history'].search([('vehicle_id', '=', vehicle.id),('start_time','>=',from_date)],
                                                                             order="end_time desc",limit=1)
                
        if trip_id:
            vehicle.write({'last_odometer_datetime':trip_id.end_time})
        if trip_odometer > 0:
            vehicle.write({'last_odometer':vehicle.last_odometer + trip_odometer})
        return trip_odometer
    
    def get_vehicle_odometer(self,vehicle):
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')
        url = "https://hk-open.tracksolidpro.com/route/rest"
        #url = "http://open.10000track.com/route/rest"
        #cookie = self.login()
        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
        }        #token = self.get_tracksolid_token()
        token = self.get_tracksolid_token_parameter()
        if token != "error":
            traccar_device_id = vehicle.traccar_uniqueID
            ir_config_obj = self.env['ir.config_parameter'].sudo()

            #utc_current = self.convert_TZ_UTC(datetime.now())
            utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if traccar_device_id: #cookie and traccar_device_id:
                if vehicle.last_odometer_datetime: 
                    from_date =  vehicle.last_odometer_datetime#vehicle.last_odometer_datetime.strftime("%Y-%M-%d %H:%M:%S")
                else:
                    from_date =  '2019-09-01 00:00:00'
                # for rec in self.env['fleet.vehicle.trip.history'].search([('vehicle_id', '=', vehicle.id)],
                #                                                          order="end_time desc", limit=1):
                #     a_date = rec.end_time or ''
                #     tmp_date = rec.end_time #.strftime("%Y-%M-%d %H:%M:%S")
                #     from_date = tmp_date

                to_date = utc_current
                body = {'method': "jimi.device.track.mileage",
                        'timestamp': utc_current,
                        'app_key': '8FB345B8693CCD00AC3E48A9D2EABBA6',
                        'access_token': token['accessToken'],
                        'v': "0.9",
                        'sign_method': "md5",
                        'format': "json",

                        'imeis': traccar_device_id,
                        'begin_time': from_date,  # 1603757920,
                        'end_time': to_date,  # 1603793920
                        'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                        'expires_in': 900
                        }
                results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                response = requests.request("POST", url, headers={}, params=body)

                print(response.status_code)
                self.create_api_log("get_vehicle_odometer", body, response.status_code, response.text)
                if response.status_code == 200:
                    res_data = json.loads(response.content.decode('utf-8'))
                    print(res_data)                                       
                    if not 'result' in res_data:
                        return vehicle.last_odometer
                    results = res_data['result']
                    if (results is None):
                        return vehicle.last_odometer 
                    print(results)
                    for result in results:

                        res = {
                            'vehicle_id': vehicle.id,
                            'duration': result['runTimeSecond'],
                            'distance': float(result['distance']) / 1000,
                            'avg_speed': result['avgSpeed'],
                            # 'max_speed':result['maxSpeed'],
                            # 'spent_fuel': result['spentFuel'],
                            # 'start_address': result['startAddress'],
                            'start_lat': result['startLat'],
                            'start_lon': result['startLng'],
                            'start_time': result['startTime'],
                            # 'end_address': result['endAddress'],
                            'end_lat': result['endLat'],
                            'end_lon': result['endLng'],
                            'end_time': result['endTime'],
                            'start_odometer': result['startMileage'],
                            'end_odometer': result['endMileage'],
                            'start_mileage': result['startMileage'],
                            'end_mileage': result['endMileage'],
                            # 'startPositionId': result['startPositionId'],
                            # 'endPositionId': result['endPositionId'],

                        }
                        trip_id = self.env['fleet.vehicle.trip.history'].search(
                            [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                             ('vehicle_id', '=', vehicle.id)])
                        if trip_id:
                            trip_id.write(res)
                        else:
                            self.env['fleet.vehicle.trip.history'].create(res)
                else:
                    token = self.get_tracksolid_token()
                    to_date = utc_current
                    body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': '8FB345B8693CCD00AC3E48A9D2EABBA6',
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",

                            'imeis': traccar_device_id,
                            'begin_time': from_date,  # 1603757920,
                            'end_time': to_date,  # 1603793920
                            'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                            'expires_in': 900
                            }
                    results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                    response = requests.request("POST", url, headers={}, params=body)
                    self.create_api_log("get_vehicle_odometer", body, response.status_code, response.text)
                    print(response.status_code)
                    if response.status_code == 200:
                        res_data = json.loads(response.content.decode('utf-8'))
                        results = res_data['result']
                        if not 'result' in res_data or (results is None):
                            return vehicle.last_odometer
                        pprint(results)
                        for result in results:

                            res = {
                                'vehicle_id': vehicle.id,
                                'duration': result['runTimeSecond'],
                                'distance': float(result['distance']) / 1000,
                                'avg_speed': result['avgSpeed'],
                                # 'max_speed':result['maxSpeed'],
                                # 'spent_fuel': result['spentFuel'],
                                # 'start_address': result['startAddress'],
                                'start_lat': result['startLat'],
                                'start_lon': result['startLng'],
                                'start_time': result['startTime'],
                                # 'end_address': result['endAddress'],
                                'end_lat': result['endLat'],
                                'end_lon': result['endLng'],
                                'end_time': result['endTime'],
                                'start_odometer': result['startMileage'],
                                'end_odometer': result['endMileage'],
                                'start_mileage': result['startMileage'],
                                'end_mileage': result['endMileage'],
                                # 'startPositionId': result['startPositionId'],
                                # 'endPositionId': result['endPositionId'],

                            }
                            trip_id = self.env['fleet.vehicle.trip.history'].search(
                                [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                                 ('vehicle_id', '=', vehicle.id)])
                            if trip_id:
                                trip_id.write(res)
                            else:
                                self.env['fleet.vehicle.trip.history'].create(res)
            odometer = self.update_trip_odometer(vehicle,from_date)
        return odometer

        
    def get_mileage(self):
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')
        url = "https://hk-open.tracksolidpro.com/route/rest"
        #url = "http://open.10000track.com/route/rest"
        #cookie = self.login()
        headers = {
            'accept': "application/json",
            'content-type': "application/json"  # ,
        }

        for vehicle in self.env['fleet.vehicle'].search([('traccar_uniqueID', '!=', False)]):
        #for vehicle in self.env['fleet.vehicle'].search([('id', 'in', [1602,1603])]):
            #token = self.get_tracksolid_token()
            token = self.get_tracksolid_token_parameter()
            if token != "error":
                traccar_device_id = vehicle.traccar_uniqueID
                ir_config_obj = self.env['ir.config_parameter'].sudo()

                #utc_current = self.convert_TZ_UTC(datetime.now())
                utc_current = fields.Datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if traccar_device_id: #cookie and traccar_device_id:
                    if vehicle.last_odometer_datetime: 
                        from_date =  vehicle.last_odometer_datetime#vehicle.last_odometer_datetime.strftime("%Y-%M-%d %H:%M:%S")
                    else:
                        from_date =  '2019-09-01 00:00:00'
                    # for rec in self.env['fleet.vehicle.trip.history'].search([('vehicle_id', '=', vehicle.id)],
                    #                                                          order="end_time desc", limit=1):
                    #     a_date = rec.end_time or ''
                    #     tmp_date = rec.end_time #.strftime("%Y-%M-%d %H:%M:%S")
                    #     from_date = tmp_date

                    to_date = utc_current
                    body = {'method': "jimi.device.track.mileage",
                            'timestamp': utc_current,
                            'app_key': '8FB345B8693CCD00AC3E48A9D2EABBA6',
                            'access_token': token['accessToken'],
                            'v': "0.9",
                            'sign_method': "md5",
                            'format': "json",

                            'imeis': traccar_device_id,
                            'begin_time': from_date,  # 1603757920,
                            'end_time': to_date,  # 1603793920
                            'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                            'expires_in': 900
                            }
                    results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                    response = requests.request("POST", url, headers={}, params=body)

                    print(response.status_code)
                    if response.status_code == 200:
                        res_data = json.loads(response.content.decode('utf-8'))
                        print(res_data)
                        if not 'result' in res_data :
                            continue
                        results = res_data['result']
                        if results is None:
                            continue
                        pprint(results)
                        for result in results:

                            res = {
                                'vehicle_id': vehicle.id,
                                'duration': result['runTimeSecond'],
                                'distance': float(result['distance']) / 1000,
                                'avg_speed': result['avgSpeed'],
                                # 'max_speed':result['maxSpeed'],
                                # 'spent_fuel': result['spentFuel'],
                                # 'start_address': result['startAddress'],
                                'start_lat': result['startLat'],
                                'start_lon': result['startLng'],
                                'start_time': result['startTime'],
                                # 'end_address': result['endAddress'],
                                'end_lat': result['endLat'],
                                'end_lon': result['endLng'],
                                'end_time': result['endTime'],
                                'start_odometer': result['startMileage'],
                                'end_odometer': result['endMileage'],
                                'start_mileage': result['startMileage'],
                                'end_mileage': result['endMileage'],
                                # 'startPositionId': result['startPositionId'],
                                # 'endPositionId': result['endPositionId'],

                            }
                            trip_id = self.env['fleet.vehicle.trip.history'].search(
                                [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                                 ('vehicle_id', '=', vehicle.id)])
                            if trip_id:
                                trip_id.write(res)
                            else:
                                self.env['fleet.vehicle.trip.history'].create(res)
                    else:
                        token = self.get_tracksolid_token()
                        to_date = utc_current
                        body = {'method': "jimi.device.track.mileage",
                                'timestamp': utc_current,
                                'app_key': '8FB345B8693CCD00AC3E48A9D2EABBA6',
                                'access_token': token['accessToken'],
                                'v': "0.9",
                                'sign_method': "md5",
                                'format': "json",
    
                                'imeis': traccar_device_id,
                                'begin_time': from_date,  # 1603757920,
                                'end_time': to_date,  # 1603793920
                                'app_key': "8FB345B8693CCD00AC3E48A9D2EABBA6",
                                'expires_in': 900
                                }
                        results = False  # get_trip_summary(cookie,traccar_device_id, OdooTraccarGroupId,from_date,to_date)
                        response = requests.request("POST", url, headers={}, params=body)
    
                        print(response.status_code)
                        if response.status_code == 200:
                            res_data = json.loads(response.content.decode('utf-8'))
                            if not 'result' in res_data:
                                continue
                            results = res_data['result']
                            if results is None:
                                continue
                            pprint(results)
                            for result in results:
    
                                res = {
                                    'vehicle_id': vehicle.id,
                                    'duration': result['runTimeSecond'],
                                    'distance': float(result['distance']) / 1000,
                                    'avg_speed': result['avgSpeed'],
                                    # 'max_speed':result['maxSpeed'],
                                    # 'spent_fuel': result['spentFuel'],
                                    # 'start_address': result['startAddress'],
                                    'start_lat': result['startLat'],
                                    'start_lon': result['startLng'],
                                    'start_time': result['startTime'],
                                    # 'end_address': result['endAddress'],
                                    'end_lat': result['endLat'],
                                    'end_lon': result['endLng'],
                                    'end_time': result['endTime'],
                                    'start_odometer': result['startMileage'],
                                    'end_odometer': result['endMileage'],
                                    'start_mileage': result['startMileage'],
                                    'end_mileage': result['endMileage'],
                                    # 'startPositionId': result['startPositionId'],
                                    # 'endPositionId': result['endPositionId'],
    
                                }
                                trip_id = self.env['fleet.vehicle.trip.history'].search(
                                    [('start_time', '=', result['startTime']), ('end_time', '=', result['endTime']),
                                     ('vehicle_id', '=', vehicle.id)])
                                if trip_id:
                                    trip_id.write(res)
                                else:
                                    self.env['fleet.vehicle.trip.history'].create(res)
            _logger.info("update_trip_odometer vehicle>>>>>>: %s fromdate >>>>>>>>>>> %s" % (vehicle,from_date))
            odometer = self.update_trip_odometer(vehicle,from_date)
        return True
    
    def convert_TZ_UTC(self, TZ_datetime):
        fmt = "%Y-%m-%d %H:%M:%S"
        # Current time in UTC
        now_utc = datetime.now(timezone('UTC'))
        TZ_datetime = datetime.now(timezone('Asia/Yangon'))
        # Convert to current user time zone
        now_timezone = now_utc.astimezone(timezone(self.env.user.tz or self.env.context.get('tz')))
        UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(
            now_timezone.strftime(fmt), fmt)
        local_datetime = datetime.strptime(TZ_datetime.strftime(fmt), fmt)
        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
        return result_utc_datetime.strftime(fmt)
    
    def get_tracksolid_token_parameter(self):
        parameter_token = self.env['ir.config_parameter'].sudo().get_param('track.solid_token')
        data = {}            
        if parameter_token:
            data['accessToken'] = parameter_token
            return data
    def create_api_log(self,method_name,body,status_code,log):
        track_solid_obj = self.env['track.solid.api.log']

        name = method_name
        if self._context.get('active_model') or self._context.get('params'):

            name = self._context.get('active_model') + ">>>>>" + method_name if self._context.get('active_model') else str(self._context.get('params')) + ">>>>>" + method_name
        data = {
                'code':status_code,
                'log':log,
                'name':name
                }
        track_solid_id = track_solid_obj.create(data)
        return  track_solid_id
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
        self.create_api_log("get_tracksolid_token",body, response.status_code, response.text)
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
            self.create_api_log("show_current_localize", body, response.status_code, response.text)
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
                self.create_api_log("show_current_localize", body, response.status_code, response.text)
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

    def geo_localize(self):
        add_to_odometer = True if self.env['ir.config_parameter'].sudo().get_param('add_to_odometer',
                                                                                   'False').lower() != 'false' else False
        # get superuser's timezone
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        if user.partner_id.tz:
            tz = timezone(user.partner_id.tz) or timezone('UTC')
        else:
            tz = timezone('UTC')

        cookie = self.login()
        for vehicle in self:
            traccar_device_id = vehicle.traccar_device_id
            if cookie and traccar_device_id:
                result = False  # get_last_position(cookie, traccar_device_id)
                if result and result[0] != 0 and result[1] != 0 and result[2]:
                    fixTime = tz.localize(result[2])
                    fixTime = fixTime.astimezone(pytz.utc)

                    res = {
                        'vehicle_latitude': result[0],
                        'vehicle_longitude': result[1],
                        'date_localization': fixTime,
                    }

                    if not self.env['fleet.vehicle.location.history'].search(
                            [('vehicle_id', '=', vehicle.id), ('date_localization', '=', result[2])]):
                        res.update({'location_history_ids': [(0, 0, {
                            'vehicle_latitude': result[0],
                            'vehicle_longitude': result[1],
                            'date_localization': result[2],
                            'name': vehicle.name,
                            'driver_name': vehicle.driver_id and vehicle.driver_id.name or '-'
                        })]
                                    })
                        if result[3] and add_to_odometer: res.update(
                            odometer=vehicle.pre_tracking_odometer + (
                                (result[3] / 1000.00) if vehicle.odometer_unit == 'kilometers' else (result[
                                                                                                         3] / 1000.00) * 0.62137))
                    # add additional engine hour
                    ir_config_obj = self.env['ir.config_parameter'].sudo()
                    OdooTraccarGroupId = ir_config_obj.get_param('odoo_traccar_groupId') or False
                    cookie = vehicle.login()
                    result_running = False  # get_device_summary(cookie, traccar_device_id,OdooTraccarGroupId)
                    if result_running and result_running[0] != 0 and result_running[1] != 0 and result_running[3]:
                        res.update({
                            'average_speed': result_running[0],
                            'max_speed': result_running[1],
                            'engine_hours': result_running[3],
                        })
                    vehicle.write(res)

        return True

    @api.model
    def schedule_trip(self):
        records_to_schedule = self.env['fleet.vehicle'].search(
            [('gps_tracking', '=', True), ('traccar_device_id', '!=', False)])
        if not records_to_schedule:
            return
        res = None
        try:
            records_to_schedule.get_trip()
            res = True
        except Exception:
            _logger.exception("Fleet Tracking Failed.")
        return res

    @api.model
    def schedule_traccar(self):
        """Schedules fleet tracking using Traccar platform.  
        """

        records_to_schedule = self.env['fleet.vehicle'].search(
            [('gps_tracking', '=', True), ('traccar_device_id', '!=', False)])
        if not records_to_schedule:
            return

        res = None
        try:
            records_to_schedule.geo_localize()
            res = True
        except Exception:
            _logger.exception("Fleet Tracking Failed.")
        return res

    def action_show_inactives(self):
        self.ensure_one()
        context = self.env.context.copy()
        context['default_vehicle_id'] = self.id
        new_ids = []
        condition = [('vehicle_id', '=', self.id),
                     ('vehicle_latitude', '!=', 0), ('vehicle_longitude', '!=', 0)]  # ('inactive_period','=', True)
        if self.date_inactive_filter:
            condition.extend([('date_localization', '>=', self.date_inactive_filter), (
                'date_localization', '<=',
                datetime.datetime.combine(self.date_inactive_filter.date(), datetime.time.max))])

        all_location_records = self.env['fleet.vehicle.location.history'].search(condition,
                                                                                 order='date_localization desc')
        if all_location_records:
            for day in all_location_records:
                if day.inactive_period: new_ids.append(day.id)
        view_id = self.env.ref('traccar_fleet_tracking.view_vehicle_location_history_tree')
        return {
            'name': _('Inactive Periods'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle.location.history',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            # 'views': [(view_id.id, 'tree')],
            'context': context,
            'domain': [('id', 'in', new_ids)]
        }


class FleetVehicleDayTrip(models.TransientModel):
    _name = "fleet.vehicle.day.trip"
    _description = 'Daily Vehicle Trip Data'
    _rec_name = 'on_date'

    @api.depends('on_date')
    def _compute_bokeh_chart(self):
        for rec in self:
            on_date = self.on_date
            day_after = on_date + datetime.timedelta(days=1)

            day_points = self.env['fleet.vehicle.location.history'].search([('vehicle_id', '=', self.vehicle_id.id),
                                                                            ('date_localization', '<', day_after),
                                                                            ('date_localization', '>=', on_date)])
            if not day_points:
                # no data
                return

            data = {
                'lat': [],
                'lon': [],
                'info': []
            }
            for point in day_points:
                data['lat'].append(point.vehicle_latitude)
                data['lon'].append(point.vehicle_longitude)
                data['info'].append(point.driver_name + ' - ' + point.date_localization.strftime("%Y-%m-%d %H:%M:%S"))

            map_options = GMapOptions(lat=data['lat'] and data['lat'][0] or 0,
                                      lng=data['lon'] and data['lon'][0] or 0, map_type="roadmap", zoom=11)

            gmaps_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
            if not gmaps_api_key:
                raise UserError(
                    _("You have not entered a Google Maps API key (under Fleet - Traccar Settings), please do so to view map views."))
            p = GMapPlot(api_key=gmaps_api_key, x_range=Range1d(), y_range=Range1d(),
                         map_options=map_options)  # , title="My Drive")

            source = ColumnDataSource(data=dict(lat=data['lat'], lon=data['lon'],
                                                info=data['info'], ))

            path = Line(x="lon", y="lat", line_width=2, line_color='blue')

            p.add_glyph(source, path)
            p.add_tools(PanTool(), WheelZoomTool(), SaveTool(),
                        HoverTool(tooltips=[("Info", "@info"), ]))
            p.sizing_mode = 'scale_width'

            script, div = components(p)
            rec.trip = '%s%s' % (div, script)

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    on_date = fields.Date(string='On Date', default=fields.Date.today(), required=True, track_visibility='always')
    trip = fields.Text(
        string='Trip',
        compute=_compute_bokeh_chart, track_visibility='always')
