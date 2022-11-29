import base64
from odoo import api, fields, models
from odoo import tools


class Meeting(models.Model):
    _inherit = 'calendar.event'
    _description = "Calendar Event"

    employee_ids = fields.Many2many(
		'hr.employee', 
		string='Employee'
	)