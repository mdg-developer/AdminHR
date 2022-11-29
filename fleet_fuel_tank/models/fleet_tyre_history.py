from odoo import api, fields, models, tools, _
from datetime import datetime, date, timedelta


class FleetTyreHistory(models.Model):
    _name = 'fleet.tyre.history'
    _description = 'Fleet Tyre History'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    date = fields.Date(string='Date')
    used_points = fields.Float(string='Used Points')
    source_doc = fields.Char(string='Source Document')
    note = fields.Char(string='Note')