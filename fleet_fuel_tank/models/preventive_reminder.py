from odoo import api, fields, models, tools, _
from datetime import datetime, date, timedelta


class PreventiveReminder(models.Model):
    _name = 'preventive.reminder'
    _description = 'Preventive Reminder'

    product_id = fields.Many2one('product.product', string='Product',domain="[('product_tmpl_id.categ_id.maintenance_type', '=', 'preventive'), '|', ('product_tmpl_id.company_id', '=', False)]")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    name = fields.Char(string='Maintenance Type', required=False)
    last_date = fields.Date(string='Last Date')
    last_odometer = fields.Float(string='Last Odometer')
    next_odometer = fields.Float(string='Alert Odometer')
    odometer_next = fields.Float(string='Next Odometer')
	
    

