from odoo import api, fields, models, _

class ResCity(models.Model):
    _name = 'res.city'
    _description="City"
    
    name = fields.Char('City Name')
    code = fields.Char('Code')
    state_id = fields.Many2one('res.country.state', string='State')
    partner_latitude = fields.Float(string="Latitude", default=0.0)
    partner_longitude = fields.Float(string="Longitude", default=0.0)
    
ResCity()

class ResTownship(models.Model):
    _name = 'res.township'
    _description="Township"
    
    name = fields.Char('Township Name')
    code = fields.Char(' Code')
    city_id = fields.Many2one('res.city', string='City')
    
ResTownship() 