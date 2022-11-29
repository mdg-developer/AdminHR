from odoo import api, fields, models, _
from geopy.distance import geodesic


class Map(models.Model):    
    _name = 'gps.map'    
    _description = 'Map'    
    
    name = fields.Char(stirng="Name")
    partner_latitude = fields.Float(string="Latitude", default=0.0)
    partner_longitude = fields.Float(string="Longitude", default=0.0)
    
    def button_create_to_map(self):
        route_id = self._context.get('active_ids')
        route_obj=self.env['route.plan'].search([('id', '=', route_id[0])])
        if self.partner_latitude and self.partner_longitude:
            arrival =  (self.partner_latitude, -self.partner_longitude)
            route_obj.arrival = arrival
            route_obj.ar1 = self.partner_latitude
            route_obj.ar2 = self.partner_longitude

    
    def button_create_from_map(self):
        route_id = self._context.get('active_ids')
        route_obj=self.env['route.plan'].search([('id', '=', route_id[0])])
        if self.partner_latitude and self.partner_longitude:
            departure =  (self.partner_latitude, -self.partner_longitude)
            route_obj.departure = departure
            route_obj.d1 = self.partner_latitude
            route_obj.d2 = self.partner_longitude
