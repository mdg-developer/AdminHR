from odoo import fields, models, api, _

class VehicleInsurance (models.Model):    
    _name = 'fleet.vehicle.insurance'
    _description = 'Vehicle Insurance'    

    name = fields.Char(string='Name', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    make_model = fields.Char(string='Make And Model')
    si = fields.Float(string='SI(Head+Trailer)')
    basic_premium = fields.Float(string='Basic Premium')
    wind_screen = fields.Float(string='Windscreen')
    srcc = fields.Float(string='S.R.C.C')
    act_god = fields.Float(string='Act of God')
    war_risk = fields.Float(string='War Risk')
    thelf = fields.Float(string='Theft')
    third_party = fields.Float(string='Third Party')
    nil_excess = fields.Float(string='Nil Excess')
    total_premium = fields.Float(string='Total Premium',readonly=True)
    expired_date = fields.Date(string='Expired Date')
    
    trailer_count = fields.Integer( string='Trainers History')
    
#     def _compute_trailer_count(self):
#         for record in self:
#             record.trailer_count = self.env['fleet.trailer.insurance'].search_count([('trailer_id', '=', record.id)])
#             
#     def open_assignation_logs(self):
#         self.ensure_one()
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Trailer Assignation Logs',
#             'view_mode': 'tree',
#             'res_model': 'fleet.trailer.insurance',
#             'domain': [('vehicle_id', '=', self.id)],
#             'context': {'default_trailer_id': self.trailer_id.id, 'default_vehicle_id': self.id}
#         }
        
    @api.model
    def create(self, vals):
        result = super(VehicleInsurance, self).create(vals)
        result.name = result.vehicle_id.name
        return result

        
    @api.onchange('si', 'basic_premium','wind_screen','srcc','act_god','war_risk','thelf','third_party','nil_excess')
    def onchange_total(self):
            for line in self:
                line.total_premium= self.si + self.basic_premium + self.wind_screen + self.srcc  + self.act_god + self.war_risk + self.thelf + self.third_party + self.nil_excess
