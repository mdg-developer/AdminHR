from odoo import api, fields, models, _
import requests
import json
import logging
import ast

_logger = logging.getLogger(__name__)


class OneSignalNotificationMessage(models.Model):
    _name = 'one.signal.notification.message'
    _rec_name = 'id'
    _description = 'one signal notification messages'

    contents = fields.Char(string='Contents', required=True, help='Content display to end user')
    headings = fields.Char(string='Headings', required=True, help='Heading display to end user' )
    subtitle = fields.Char(string='Subtitle', help='SubTitle')

    employee_id = fields.Many2one('hr.employee', string='Employee')
    app_id = fields.Many2one('one.signal.notification.apps', string='App', help='Message send to the application')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    has_read = fields.Boolean('Has read?', default=False)
    state = fields.Selection([('draft', 'Draft'), ('sent', 'Sent'), ('fail', 'Failed')], string='Status', default='draft', help='Status of the notification')

    # Response from One Signal
    reason = fields.Text(string='Reason', help='Response of the Notification')
    external_id = fields.Char(string='One Signal External Id')
    one_signal_notification_id = fields.Char(string='Notification Id')
    recipients_count = fields.Integer(string='Recipients Count')
    message_type =  fields.Selection(
        string="Message Type",
        selection=[
            ('reminder', 'Reminder'),
            ('announcement', 'Announcement'),
            ('none', 'None'),
        ], default="none",
    )
    def update_send_msg_results(self,data_res):
        apps = self.env['one.signal.notification.apps'].sudo().search([], limit=1)
        
        employee_id = contents = None
        reason = ''
        if data_res:
            if apps:
                data = {}
                for app_record in apps:
                    data['app_api_key'] = app_record.app_api_key
                    data['app_id'] = app_record.app_id
                data['include_external_user_ids'] = [str(data_res.employee_id.id)]
                data['contents'] = data_res.contents
                response = self.send_notification(data)
                response_json = response.json()
                if response.status_code == 200:
                    reason = str(response.status_code) + ' ' + str(response.reason)
                    if 'errors' in response_json:
                        reason += ' ' + str(response_json['errors'])
                    if 'warnings' in response_json:
                        reason += ' ' + str(response_json['warnings'])
                    value = {
                             'state':'sent',
                             'reason':reason,
                             'external_id': response_json.get('external_id', False) or False,
                             'one_signal_notification_id': response_json['id'] or False,
                             'recipients_count': response_json.get('recipients',False) or False,
                             
                             }
                    data_res.sudo().write(value)    
                        
                else:
                    
                    value = {
                             'state':'fail',
                             'reason':str(response.status_code) + ' ' + str(response.reason) + ' ' + str(response_json['errors']),
                             'external_id': False,
                             'one_signal_notification_id':  False,
                             'recipients_count': response_json.get('recipients',False) or False,
                             
                             }
                    data_res.sudo().write(value) 
            
    @api.model
    def create(self, vals):
        res = super(OneSignalNotificationMessage, self.sudo()).create(vals)
        self.update_send_msg_results(res)
        return res

    
#     @api.model    
#     def create(self, vals):
#         context = dict(self._context or {})
#         apps = self.env['one.signal.notification.apps'].sudo().search([], limit=1)
#         if apps:
#             data = {}
#             for app_record in apps:
#                 data['app_api_key'] = app_record.app_api_key
#                 data['app_id'] = app_record.app_id
#             data['include_external_user_ids'] = [str(vals.get('employee_id'))]
#             data['contents'] = vals['contents']
#             if vals['headings']:
#                 data['headings'] = vals['headings']
# 
#             if vals.get('subtitle'):
#                 data['subtitle'] = vals['subtitle']
#             response = self.send_notification(data)
#             response_json = response.json()
#             if response.status_code == 200:
#                 vals['state'] = 'sent'
#                 vals['reason'] = str(response.status_code) + ' ' + str(response.reason)
#  
#                 vals['external_id'] = response_json.get('external_id', False) or False
#                 vals['one_signal_notification_id'] = response_json['id'] or False
#                 vals['recipients_count'] = response_json['recipients'] or False
#                 if 'errors' in response_json:
#                     vals['reason'] += ' ' + str(response_json['errors'])
#                 if 'warnings' in response_json:
#                     vals['reason'] += ' ' + str(response_json['warnings'])
#             else:
#                 vals['state'] = 'fail'
#                 vals['reason'] = str(response.status_code) + ' ' + str(response.reason) + ' ' + str(response_json['errors'])
#                 vals['external_id'] = False
#                 vals['one_signal_notification_id'] = False
#                 vals['recipients_count'] = False
#                 if 'warnings' in response_json:
#                     vals['reason'] += ' ' + str(response_json['warnings'])
                    
#         result = super(OneSignalNotificationMessage, self).sudo().create(vals)
#         return result

    def action_retry(self):
        self.state = 'draft'

    @staticmethod
    def send_notification(data):
        header = {}
        response = False
        payload = {}
        headings = {}
        messages = {}
        subtitle = {}
        external_user_id = data.get('include_external_user_ids')
        app_id = data.get('app_id', False) or False
        app_api_auth_key = data.get('app_api_key', False) or False
        if app_id and app_api_auth_key:
            header = {'Content-Type': 'application/json; charset=utf-8',
                      'Authorization': 'Basic %s' % app_api_auth_key}
            payload['app_id'] = app_id
            payload['include_external_user_ids'] = external_user_id

            if data.get('subtitle' or False) or False:
                subtitle['en'] = data.get('subtitle')
                payload['subtitle'] = subtitle

            if data.get('contents' or False) or False:
                messages['en'] = data.get('contents')
                payload['contents'] = messages

            else:
                _logger.info('Please provide the "contents" '
                             'eg: {"en": "English Message", "es": "Spanish Message"} '
                             'in the Input Request to the send_notification() method')
            if data.get("headings" or False) or False:
                headings["en"] = data.get("headings")
                payload['headings'] = headings
            else:
                _logger.info('Please provide the "headings" '
                             'eg: {"en": "English Title", "es": "Spanish Title"} '
                             'in the Input Request to the send_notification() method')

        else:
            _logger.info('Please provide the "app_id" & "app_api_key" in the Input Request to the '
                         'send_notification() method')

        payload['android_sound'] = "default"
        payload['small_icon'] = "ic_stat_onesignal_default.png"
        payload['channel_for_external_user_ids'] = "push"
        if header and payload:
            payload = json.dumps(payload)
            response = requests.post('https://onesignal.com/api/v1/notifications', headers=header, data=payload)
            _logger.info('Response: %s' % str(response.status_code) + ' ' + str(response.reason))
            _logger.info('Response Json: %s' % str(response.json()))

        return response
