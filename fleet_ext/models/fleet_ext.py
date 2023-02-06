from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class fleet_vehicle(models.Model):
    _inherit = 'fleet.vehicle'
    _description = 'Vehicle'

    hr_driver_id = fields.Many2one('hr.employee', 'Driver', required=True, tracking=True, help='Driver of the vehicle',
                                   copy=False)
    hr_future_driver_id = fields.Many2one('hr.employee', 'Future Driver', tracking=True,
                                          help='Future Driver of the vehicle',
                                          copy=False)
    hr_manager_id = fields.Many2one('hr.employee', 'Fleet Manager', required=True, tracking=True,
                                    help='Fleet Manager of the vehicle', copy=False)
    tyre_points_per_km = fields.Float(string='Tyre Points')
    engine_points_per_km = fields.Float(string='Engine Oil Points')
    tyre_points_per_mmk = fields.Float(string='Tyre Points')
    engine_points_per_mmk = fields.Float(string='Engine Oil Points')
    image_128 = fields.Image(related='', readonly=False)
    # odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Trip Odometer', search="_search_odometer",
    #     help='Odometer measure of the vehicle at the moment of this log')
    trip_odometer = fields.Float(string='Trip Odometer')
    last_odometer = fields.Float(string='Last Odometer')
    last_odometer_datetime = fields.Datetime('Last Odometer Date', required=False)

    # def _search_odometer(self, operator, value):
    #     value = float(value)
    #     vehicles = self.env['fleet.vehicle'].search([])
    #     valid_vehicles = self.env['fleet.vehicle']

    #     for vehicle in vehicles:
    #         if operator == '>' and vehicle.odometer > value:
    #             valid_vehicles |= vehicle
    #         elif operator == '<' and vehicle.odometer < value:
    #             valid_vehicles |= vehicle
    #         elif operator == '>=' and vehicle.odometer >= value:
    #             valid_vehicles |= vehicle
    #         elif operator == '<=' and vehicle.odometer <= value:
    #             valid_vehicles |= vehicle
    #         elif operator == '=' and vehicle.odometer == value:
    #             valid_vehicles |= vehicle
    #         elif operator == '!=' and vehicle.odometer != value:
    #             valid_vehicles |= vehicle

    #     return [('id', 'in', valid_vehicles.ids)]

    def action_open_odometer_log(self):
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet_ext', xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    # @api.model
    # def create(self, vals):
    #     res = super(fleet_vehicle, self).create(vals)
    #     if 'hr_driver_id' in vals and vals['hr_driver_id']:
    #         emp_driver = self.env['hr.employee'].browse(vals['hr_driver_id'])
    #         res.create_driver_history(emp_driver)
    #     if 'future_driver_id' in vals and vals['future_driver_id']:
    #         state_waiting_list = self.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
    #         states = res.mapped('state_id').ids
    #         if not state_waiting_list or state_waiting_list.id not in states:
    #             future_driver = self.env['res.partner'].browse(vals['future_driver_id'])
    #             future_driver.sudo().write({'plan_to_change_car': True})
    #     return res
    #
    def write(self, vals):
        if 'hr_driver_id' in vals and vals['hr_driver_id']:
            driver_id = vals['hr_driver_id']
            self.filtered(lambda v: v.driver_id.id != driver_id).create_driver_history(driver_id)
            # emp_driver = self.env['hr.employee'].browse(driver_id)
            # self.filtered(lambda v: v.driver_id.id != driver_id).create_driver_history(emp_driver.id)
            # if emp_driver:
            #     self.create_driver_history(emp_driver.id)
            # self.create_driver_history(driver_id)

        if 'hr_future_driver_id' in vals and vals['hr_future_driver_id']:
            state_waiting_list = self.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
            states = self.mapped('state_id').ids if 'state_id' not in vals else [vals['state_id']]
            if not state_waiting_list or state_waiting_list.id not in states:
                hr_future_driver = self.env['hr.employee'].browse(vals['hr_future_driver_id'])
                if hr_future_driver:
                    self.sudo().write({'plan_to_change_car': True})

        old_odometer = self.last_odometer
        res = super(fleet_vehicle, self).write(vals)
        if 'active' in vals and not vals['active']:
            self.mapped('log_contracts').write({'active': False})
        if 'last_odometer' in vals:
            data = {
                'vehicle_id': self.id,
                'user_id': self.env.user.id,
                'date': fields.Date.today(),
                'old_odometer': old_odometer,
                'odometer': vals.get('last_odometer'),
            }
            self.env['vehicle.odometer.log'].sudo().create(data)
        return res

    def _close_driver_history(self):
        self.env['fleet.vehicle.assignation.log'].search([
            ('vehicle_id', 'in', self.ids),
            ('hr_driver_id', 'in', self.hr_driver_id.ids),
            ('date_end', '=', False)
        ]).write({'date_end': fields.Date.today()})

    def create_driver_history(self, driver_id):
        # for vehicle in self:
        # res_partner = self.env['res.partner'].search([('id', '=', driver_id)])
        # if res_partner:
        #     self.env['fleet.vehicle.assignation.log'].create({
        #         'vehicle_id': vehicle.id,
        #         'driver_id': res_partner.id,
        #         'date_start': fields.Date.today(),
        #     })
        # else:
        # hr_emp = self.env['hr.employee'].search([('id', '=', driver_id)])
        # if hr_emp:
        #     self.env['fleet.vehicle.assignation.log'].create({
        #         'vehicle_id': vehicle.id,
        #         'driver_id': hr_emp.id,
        #         'date_start': fields.Date.today(),
        #     })
        #     print(vehicle.id,hr_emp.id)
        for vehicle in self:
            self.env['fleet.vehicle.assignation.log'].sudo().create(
                {
                    'vehicle_id': vehicle.id,
                    'hr_driver_id': driver_id,
                    'driver_id': 1,
                    'date_start': fields.Date.today(),
                }
            )

    def action_accept_driver_change(self):
        # Find all the vehicles for which the driver is the future_driver_id
        # remove their driver_id and close their history using current date
        # partner = self.mapped('future_driver_id').id
        # res_partner = self.env['res.partner'].search([('id', '=', partner)])
        # res_users = self.env['res.users'].search([('partner_id', '=', res_partner.id)])
        # hr_emp = self.env['hr.employee'].search([('user_id', '=', res_users.id)])
        # vehicles = self.search([('hr_driver_id', 'in', hr_emp.ids)])
        # self.write({'hr_driver_id': False})

        for vehicle in self:
            if vehicle.hr_future_driver_id:
                vehicle.sudo().write({'plan_to_change_car': False})
                hr_emp_future_driver = self.env['hr.employee'].search([('id', '=', vehicle.hr_future_driver_id.id)])
                vehicle.hr_driver_id = hr_emp_future_driver.id
                vehicle.hr_future_driver_id = False
            else:
                raise UserError(_("Future Driver does not exit!"))

        self._close_driver_history()

    def update_vehicle_last_odometer(self):
        vehicles = self.env['fleet.vehicle'].sudo().search([])
        if vehicles:
            for vehicle in vehicles:
                vehicle.get_device_odometer()
                # last_odometer = vehicle.last_odometer + \

                # print("odometer : ", last_odometer)
                # vehicle.write({
                #     'last_odometer': last_odometer
                # })

    @api.model
    def update_expired_license_reminder(self):
        # This method is called by a cron task 'ir_cron_vehicle_license_expired_action_reminder'
        date_today = fields.Date.today()
        outdated_date = date_today + relativedelta(days=+30)
        # next_reminded_date = outdated_date
        nearly_expired_vehicles = self.search([('active', '=', True),
                                               ('license_expired_date', '<', outdated_date),
                                               ('license_expired_date', '>=', date_today)]
                                              )

        if nearly_expired_vehicles:
            expired_vehicles_list = [vehicle.name for vehicle in nearly_expired_vehicles]

            # send message reminder on Administration/Access Right group users
            odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
            self.env['mail.message'].create({
                'author_id': odoobot_id,  # creator id
                'model': 'mail.channel',
                'message_type': 'comment',
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'subject': 'သက်တမ်းတိုးရန်',
                'body': "Following Vehicle Licenses will expired soon! \n{}".format(expired_vehicles_list),
                'channel_ids': [(4, self.env.ref(
                    'fleet_ext.channel_fleet_expired_reminder').id)],
                'res_id': self.env.ref('fleet_ext.channel_fleet_expired_reminder').id,
            })

        # if date_today == next_reminded_date:
            # add schedule activity on each vehicle where their license will expired soon
            for vehicle in nearly_expired_vehicles:
                vehicle.activity_schedule(
                    'fleet_ext.mail_act_fleet_license_to_renew', vehicle.license_expired_date,
                    note="License သက်တမ်းတိုးရန်",
                )

    class FleetVehicleCost(models.Model):
        _inherit = 'fleet.vehicle.cost'

        vendor_bill_ref = fields.Char(string='Vendor Bill Ref')
        po_ref = fields.Char(string='PO Ref')
        source_doc = fields.Char(string='Source Doc')

    class FleetVehicleAssignationLogInherit(models.Model):
        _inherit = 'fleet.vehicle.assignation.log'

        hr_driver_id = fields.Many2one('hr.employee', string="Driver", required=True)
        driver_id = fields.Many2one('res.partner', string="Driver")

    class VehicleOdometerLog(models.Model):
        _name = 'vehicle.odometer.log'
        _description = 'Vehicle Odometer Log'

        vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
        date = fields.Date(string='Date')
        user_id = fields.Many2one('res.users', string='Updated By')
        old_odometer = fields.Float(string='Old Odometer')
        odometer = fields.Float(string='New Odometer')
