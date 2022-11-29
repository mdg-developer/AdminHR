from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class track_solid_api_log(models.Model):
    _name = "track.solid.api.log"

    name = fields.Char('Name')
    date = fields.Datetime(string="Date",default=fields.Datetime.now)
    log = fields.Char('Log')
    code = fields.Char('Status code')
    value= fields.Text('Body')