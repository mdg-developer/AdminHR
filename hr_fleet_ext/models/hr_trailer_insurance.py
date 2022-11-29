from odoo import fields, models, api, _

class TrailerInsurance (models.Model):    
    _name = 'fleet.trailer.insurance'
    _description = 'Trailer Insurance'    

    name = fields.Char(string='Name', readonly=True)
    trailer_id = fields.Many2one('trip.trailer', string="Trailer", required=True)
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
    total_premium = fields.Float(string='Total Premium', readonly=True)
    expired_date = fields.Date(string='Expired Date')
    
    vehicle_count = fields.Integer(string='Vehicles History')
#     
#     def _compute_vehicle_count(self):
#         for record in self:
#             record.vehicle_count = self.env['fleet.vehicle.insurance'].search_count([('vehicle_id', '=', record.id)])
#             
#     def open_assignation_log(self):
#         self.ensure_one()
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Vehicle Assignation Logs',
#             'view_mode': 'tree',
#             'res_model': 'fleet.vehicle.insurance',
#             'domain': [('vehicle_id', '=', self.id)],
#             'context': {'default_trailer_id': self.trailer_id.id, 'default_vehicle_id': self.id}
#         }
        
    @api.model
    def create(self, vals):
        result = super(TrailerInsurance, self).create(vals)
        result.name = result.trailer_id.name
        return result

        
    @api.onchange('si', 'basic_premium','wind_screen','srcc','act_god','war_risk','thelf','third_party','nil_excess')
    def onchange_total(self):
            for line in self:
                line.total_premium= self.si + self.basic_premium + self.wind_screen + self.srcc  + self.act_god + self.war_risk + self.thelf + self.third_party + self.nil_excess
