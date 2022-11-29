from odoo import api, fields, models, _


class FuelFillingHistory(models.Model):
    _inherit = 'fuel.filling.history'

    trip_consumption_line_id = fields.Many2one('trip.fuel.consumption', string='Trip Consumption ID',ondelete='cascade', index=True, copy=False)
    trip_fuel_in_line_id = fields.Many2one('trip.fuel.in', string='Trip Fuel In ID',ondelete='cascade', index=True, copy=False)


class compsuption_great_average(models.Model):
    _inherit = 'compsuption.great.average'
	
    trip_consumption_line_id = fields.Many2one('trip.fuel.consumption', string='Trip Consumption ID')


class fleet_vehicle_log_fuel(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'
    
    trip_fuel_in_line_id = fields.Many2one('trip.fuel.in', string='Trip Fuel In ID')


class FleetVehicleCost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    trip_fuel_in_line_id = fields.Many2one('trip.fuel.in', string='Trip Fuel In ID')