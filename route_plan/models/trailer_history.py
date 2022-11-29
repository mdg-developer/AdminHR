from odoo import api, fields, models, _


class TrailerAssignationLog(models.Model):
    _name = "trailer.assignation.log"
    _description = "Trailers history on a vehicle"
    _order = "create_date desc"

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    trailer_id = fields.Many2one('trip.trailer', string="Trailer", required=True)
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    trailer_id = fields.Many2one('trip.trailer', string="Trailer")
    future_trailer_id = fields.Many2one('trip.trailer', string="Future Trailer")
    trailer_assignation_date = fields.Date('Trailer Assignation Date')
    trailer_location = fields.Char('Trailer Location')
    log_trailers = fields.One2many('trailer.assignation.log', 'vehicle_id', string='Trailer History')
    trailer_count = fields.Integer('Trailer Count', compute='_compute_trailer_count')
    day_trip = fields.Boolean('Day/Plan Trip')

    def _compute_trailer_count(self):
        for record in self:
            record.trailer_count = self.env['trailer.assignation.log'].search_count([('vehicle_id', '=', record.id)])

    def open_trailer_assignation_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trailer Assignation Logs',
            'view_mode': 'tree',
            'res_model': 'trailer.assignation.log',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_trailer_id': self.driver_id.id, 'default_vehicle_id': self.id}
        }
            
    def _close_trailer_history(self):
        self.env['trailer.assignation.log'].search([
            ('vehicle_id', 'in', self.ids),
            ('trailer_id', 'in', self.mapped('trailer_id').ids),
            ('date_end', '=', False)
        ]).write({'date_end': fields.Date.today()})

    def create_trailer_history(self, trailer_id):
        for vehicle in self:
            self.env['trailer.assignation.log'].create({
                'vehicle_id': vehicle.id,
                'trailer_id': trailer_id,
                'date_start': fields.Date.today(),
            })
            
    def action_accept_trailer_change(self):
        vehicles = self.search([('trailer_id', 'in', self.mapped('future_trailer_id').ids)])
        vehicles._close_trailer_history()
        vehicles.write({'trailer_id': False})
        for vehicle in self:
            vehicle.trailer_id = vehicle.future_trailer_id
            vehicle.future_trailer_id = False

    @api.model
    def create(self, vals):
        res = super(FleetVehicle, self).create(vals)
        if 'trailer_id' in vals and vals['trailer_id']:
            res.create_trailer_history(vals['trailer_id'])
        return res
    
    def write(self, vals):
        if 'trailer_id' in vals and vals['trailer_id']:
            trailer_id = vals['trailer_id']
            self.filtered(lambda v: v.trailer_id.id != trailer_id).create_trailer_history(trailer_id)
        return super(FleetVehicle, self).write(vals)
