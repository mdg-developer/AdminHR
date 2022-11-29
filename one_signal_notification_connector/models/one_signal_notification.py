from odoo import models, fields, _


class OneSignalNotificationUserAccount(models.Model):
    _name = 'one.signal.notification.user.account'
    _rec_name = 'user_auth_key'

    email = fields.Char(string='Email', help='Email Id with which one signal is created')
    user_auth_key = fields.Char(string='User Auth Key', required=True, help='User Account Auth Key')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string='Is Active?', default=True)


class OneSignalNotificationApps(models.Model):
    _name = 'one.signal.notification.apps'

    name = fields.Char(string='Name', help='Name of the App')
    app_id = fields.Char(string='App ID', help='One Signal App Id')
    app_api_key = fields.Char(string='App Api Key', help='One Signal API Auth Key')
    user_auth_key_id = fields.Many2one('one.signal.notification.user.account', string='User Auth Key', required=False,
                                       help='User Account Auth Key')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string='Is Active?', default=True)
