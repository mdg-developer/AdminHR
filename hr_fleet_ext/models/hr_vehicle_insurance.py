from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _


class VehicleInsurance(models.Model):
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
    total_premium = fields.Float(string='Total Premium', readonly=True)
    expired_date = fields.Date(string='Expired Date')
    insurance_company = fields.Char(string='Insurance Company')
    ncb = fields.Char(string="NCB")

    trailer_count = fields.Integer(string='Trainers History')

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

    @api.onchange('si', 'basic_premium', 'wind_screen', 'srcc', 'act_god', 'war_risk', 'thelf', 'third_party',
                  'nil_excess')
    def onchange_total(self):
        for line in self:
            line.total_premium = self.si + self.basic_premium + self.wind_screen + self.srcc + self.act_god + self.war_risk + self.thelf + self.third_party + self.nil_excess

    @api.model
    def update_expired_insurance_reminder(self):
        # This method is called by a cron task 'ir_cron_vehicle_license_expired_action_reminder'
        date_today = fields.Date.today()
        outdated_days = date_today + relativedelta(days=+21)
        nearly_insurance_expired_vehicles = self.search([
            ('expired_date', '<', outdated_days),
            ('expired_date', '>=', date_today)]
        )

        if nearly_insurance_expired_vehicles:
            insurance_expired_vehicles_list = [vehicle.name for vehicle in nearly_insurance_expired_vehicles]

            # send message reminder on Administration/Access Right group users
            odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
            self.env['mail.message'].create({
                'author_id': odoobot_id,  # creator id
                'model': 'mail.channel',
                'message_type': 'comment',
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'subject': 'သက်တမ်းတိုးရန်',
                'body': "Following Vehicle Insurance Licenses will expired soon! \n{}".format(insurance_expired_vehicles_list),
                'channel_ids': [(4, self.env.ref(
                    'hr_fleet_ext.channel_fleet_insurance_expired_reminder').id)],
                'res_id': self.env.ref('hr_fleet_ext.channel_fleet_insurance_expired_reminder').id,
            })
