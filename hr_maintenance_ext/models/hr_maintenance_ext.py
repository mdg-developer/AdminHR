from odoo import fields, models, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime, DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
from pytz import timezone, UTC


def get_utc_datetime(tz, local_dt_str):
    local_datetime = datetime.strptime(local_dt_str, DT_FORMAT)
    utc_datetime = tz.localize(local_datetime.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
    return utc_datetime.strftime(DT_FORMAT)


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'
    _description = 'Maintenance'

    # def get_default_user(self):
    #     if self.maintenance_team_id:
    #         user = self.maintenance_team_id.member_ids[0]
    #         return user.id
    #     else:
    #         return False

    name = fields.Char(string='Name', required=False)
    login_user = fields.Many2one('res.users', string='Login User', default=lambda self: self.env.user)
    code = fields.Char(string='Code')
    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    driver_id = fields.Many2one('hr.employee', string='Driver', related='vehicle_id.hr_driver_id', readonly=False,
                                store=True)
    maintenance_team_id = fields.Many2one('maintenance.team', string='Team', required=False, default=False,
                                          check_company=True, domain="[('company_id', '=', company_id)]")
    user_id = fields.Many2one('res.users', string='Technician', tracking=True, default=False)
    plan_duration = fields.Float(string='Planned Duration')
    actual_duration = fields.Float(string='Actual Duration')
    duration_days = fields.Float(string='Actual Duration Days', compute='compute_duration')
    duration_hrs = fields.Float(string='Actual Duration Hours', compute='compute_duration')
    image = fields.Binary(string='Image')
    image1 = fields.Binary(string='Image')
    image2 = fields.Binary(string='Image')
    image3 = fields.Binary(string='Image')
    image4 = fields.Binary(string='Image')
    image5 = fields.Binary(string='Image')
    image_filename = fields.Char("Image Name")
    image1_filename = fields.Char("Image 1 Name")
    image2_filename = fields.Char("Image 2 Name")
    image3_filename = fields.Char("Image 3 Name")
    image4_filename = fields.Char("Image 4 Name")
    image5_filename = fields.Char("Image 5 Name")
    description = fields.Text('Description')
    location_id = fields.Many2one('stock.location', string='Location')
    qty = fields.Float(string='Quantity')
    product_id = fields.Many2one('product.product', string='Product')
    start_date = fields.Datetime('Start Datetime',
                                 help="Date the maintenance team plans the maintenance.  It should not differ much from the Request Date. ")
    end_date = fields.Datetime('End Datetime')
    purchase_line = fields.One2many('purchase.order', 'line_id', string='Maintenance Lines', copy=True, auto_join=True)
    category_id = fields.Many2one('maintenance.equipment.category', related='equipment_id.category_id',
                                  string='Product Category', store=True, readonly=True)
    warehouse_ids = fields.One2many('warehouse.issue', 'line_id', string='Warehouse Lines', copy=True, auto_join=True)
    maintenance_product_ids = fields.One2many('maintenance.product', 'line_id', string='Maintenance Product', copy=True,
                                              auto_join=True)
    state = fields.Selection([
        ('propose', 'Propose'),
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approved', 'Approved'),
        ('start', 'Start'),
        ('reproposed', 'Re-Propose'),
        ('resubmitted', 'Resubmitted'),
        ('approve', 'Approved Again'),
        ('qc', 'QC'),
        ('done', 'Done'),
        ('reject', 'Rejected')
    ], string='Status', readonly=True, index=True, copy=False, default='propose', tracking=True)
    is_branch_manager = fields.Boolean(string='Is Branch Manager?', default=False)
    spare1_id = fields.Many2one('hr.employee', string='Spare 1')
    spare2_id = fields.Many2one('hr.employee', string='Spare 2')
    total_service_cost = fields.Float(string='Total Service Cost', compute='_compute_total_service_cost')
    maintenance_type = fields.Selection(
        [('corrective', 'Corrective'), ('preventive', 'Preventive'), ('operation', 'Operation')],
        string='Maintenance Type', default="corrective")

    def name_get(self):
        result = []
        for req in self:
            name = req.code if req.code else ''
            result.append((req.id, name))
        return result

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        if self.vehicle_id:
            if self.vehicle_id.company_id:
                self.company_id = self.vehicle_id.company_id
            else:
                self.company_id = self.env.company
            self.spare1_id = self.vehicle_id.spare_id

    @api.depends('purchase_line')
    def _compute_total_service_cost(self):
        for rec in self:
            total_cost = 0
            for line in rec.purchase_line:
                total_cost += line.amount_total
            rec.total_service_cost = total_cost

    @api.depends('start_date', 'end_date')
    def compute_duration(self):
        for record in self:
            days = 0
            hours = 0
            if record.start_date and record.end_date:
                # time_diff = record.end_date - record.start_date
                # days = time_diff.days
                # hours = time_diff.seconds / 3600
                # if hours >= 18:
                #     days += 1
                # elif hours > 6:
                #     days += 0.5
                time_diff = record.end_date - record.start_date
                days = time_diff.days
                hours = time_diff.seconds / 3600
            record.duration_days = days
            record.duration_hrs = hours

    @api.onchange('start_date', 'end_date')
    @api.constrains('start_date', 'end_date')
    def check_date_valid(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise ValidationError(_('Start date must be less than end date.'))

    def button_submit(self):
        self.state = 'submit'
        if self.driver_id:
            one_signal_values = {'employee_id': self.driver_id.branch_id.manager_id.id,
                                 'contents': _('Maintenance Request: %s submitted maintenance request %s.') % (
                                 self.driver_id.name, self.code),
                                 'headings': _('WB B2B : Maintenance Request Submitted')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def button_confirm(self):
        self.state = 'approve'
        if self.warehouse_ids:
            for line in self.warehouse_ids:
                same_picking = self.env['stock.picking'].search([('maintenance_request_id', '=', self.id),
                                                                 ('location_id', '=', line.location_id.id)
                                                                 ])
                if same_picking:
                    vals = {
                        'picking_id': same_picking.id,
                        'picking_type_id': same_picking.picking_type_id.id,
                        'company_id': same_picking.location_id.company_id.id,
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': same_picking.location_id.id,
                        'location_dest_id': same_picking.location_dest_id.id,
                        'product_uom_qty': line.qty,
                        'maintenance_line_id': line.id
                    }
                    stock_move = self.env['stock.move'].create(vals)
                    same_picking.write({
                        'move_lines': [(4, stock_move.id)]
                    })
                else:
                    if line.location_id:
                        picking_type = self.env['stock.picking.type'].search([
                            ('company_id', '=', line.location_id.company_id.id),
                            ('code', '=', 'outgoing'),
                            ('default_location_src_id', 'in', [line.location_id.id, line.location_id.location_id.id])],
                            limit=1)
                        print("picking type : ", picking_type)
                        customer_location = self.env['stock.location'].search([
                            ('usage', '=', 'customer')])
                        vals = {
                            'state': 'draft',
                            'partner_id': line.location_id.company_id.partner_id.id,
                            'scheduled_date': self.start_date,
                            'origin': self.code,
                            'location_id': line.location_id.id,
                            'picking_type_id': picking_type.id,
                            'location_dest_id': customer_location.id,
                            # 'immediate_transfer': True,
                            'maintenance_request_id': self.id
                        }
                        picking_obj = self.env['stock.picking'].create(vals)
                        if picking_obj:
                            picking_obj.write({
                                'move_lines': [(0, 0, {
                                    'picking_id': picking_obj.id,
                                    'picking_type_id': picking_obj.picking_type_id.id,
                                    'company_id': line.location_id.company_id.id,
                                    'name': line.product_id.name,
                                    'product_id': line.product_id.id,
                                    'product_uom': line.product_id.uom_id.id,
                                    'location_id': picking_obj.location_id.id,
                                    'location_dest_id': picking_obj.location_dest_id.id,
                                    'product_uom_qty': line.qty,
                                    'maintenance_line_id': line.id
                                })]
                            })
        if self.driver_id:
            one_signal_values = {'employee_id': self.driver_id.id,
                                 'contents': _('Maintenance Request: %s approved maintenance request %s.') % (
                                 self.driver_id.branch_id.manager_id.name, self.code),
                                 'headings': _('WB B2B : Maintenance Request Approved')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        if self.vehicle_id:
            one_signal_values = {'employee_id': self.vehicle_id.incharge_id.id,
                                 'contents': _('Maintenance Request: %s approved maintenance request %s.') % (
                                 self.driver_id.branch_id.manager_id.name, self.code),
                                 'headings': _('WB B2B : Maintenance Request Approved')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def button_approve(self):
        self.state = 'approved'
        if self.warehouse_ids:
            for line in self.warehouse_ids:
                same_picking = self.env['stock.picking'].search([('maintenance_request_id', '=', self.id),
                                                                 ('location_id', '=', line.location_id.id)
                                                                 ])
                if same_picking:
                    vals = {
                        'picking_id': same_picking.id,
                        'picking_type_id': same_picking.picking_type_id.id,
                        'company_id': same_picking.location_id.company_id.id,
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': same_picking.location_id.id,
                        'location_dest_id': same_picking.location_dest_id.id,
                        'product_uom_qty': line.qty,
                        'maintenance_line_id': line.id
                    }
                    stock_move = self.env['stock.move'].create(vals)
                    same_picking.write({
                        'move_lines': [(4, stock_move.id)]
                    })
                else:
                    if line.location_id:
                        picking_type = self.env['stock.picking.type'].search([
                            ('company_id', '=', line.location_id.company_id.id),
                            ('code', '=', 'outgoing'),
                            ('default_location_src_id', 'in', [line.location_id.id, line.location_id.location_id.id])],
                            limit=1)
                        print("picking type : ", picking_type)
                        customer_location = self.env['stock.location'].search([
                            ('usage', '=', 'customer')])
                        vals = {
                            'state': 'draft',
                            'partner_id': line.location_id.company_id.partner_id.id,
                            'scheduled_date': self.start_date,
                            'origin': self.code,
                            'location_id': line.location_id.id,
                            'picking_type_id': picking_type.id,
                            'location_dest_id': customer_location.id,
                            # 'immediate_transfer': True,
                            'maintenance_request_id': self.id
                        }
                        picking_obj = self.env['stock.picking'].create(vals)
                        if picking_obj:
                            picking_obj.write({
                                'move_lines': [(0, 0, {
                                    'picking_id': picking_obj.id,
                                    'picking_type_id': picking_obj.picking_type_id.id,
                                    'company_id': line.location_id.company_id.id,
                                    'name': line.product_id.name,
                                    'product_id': line.product_id.id,
                                    'product_uom': line.product_id.uom_id.id,
                                    'location_id': picking_obj.location_id.id,
                                    'location_dest_id': picking_obj.location_dest_id.id,
                                    'product_uom_qty': line.qty,
                                    'maintenance_line_id': line.id
                                })]
                            })

        if self.driver_id:
            one_signal_values = {'employee_id': self.driver_id.id,
                                 'contents': _('Maintenance Request: %s approved maintenance request %s.') % (
                                 self.driver_id.branch_id.manager_id.name, self.code),
                                 'headings': _('WB B2B : Maintenance Request Approved')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        if self.vehicle_id:
            one_signal_values = {'employee_id': self.vehicle_id.incharge_id.id,
                                 'contents': _('Maintenance Request: %s approved maintenance request %s.') % (
                                 self.driver_id.branch_id.manager_id.name, self.code),
                                 'headings': _('WB B2B : Maintenance Request Approved')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        # one_signal_values = {'employee_id': self.employee_id.id,
        #                     'contents': _('Maintenance Request: %s .') % self.equipment_id.name,
        #                     'headings': _('WB B2B : Maintenance Request %s For %s of %s .') % (self.driver_id.name or '',self.equipment_id.name or '',self.vehicle_id.name or '')}

    def button_reject(self):
        self.state = 'reject'

    def button_reject_again(self):
        self.state = 'reject'

    def button_set_to_draft(self):
        self.state = 'propose'

    # def button_set_to_repropose(self):
    #     self.state = 'reproposed'

    def button_start(self):
        self.state = 'start'
        # self.start_date = datetime.now()

    def button_repropose(self):
        self.state = 'reproposed'

    def button_resubmitted(self):
        self.state = 'resubmitted'
        if self.driver_id:
            one_signal_values = {'employee_id': self.driver_id.branch_id.manager_id.id,
                                 'contents': _('Maintenance Request: %s resubmitted maintenance request %s.') % (
                                 self.driver_id.name, self.code),
                                 'headings': _('WB B2B : Maintenance Request Resubmitted')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def button_qc(self):
        self.state = 'qc'

    def button_done(self):
        self.state = 'done'
        # self.end_date = datetime.now()

    @api.onchange('maintenance_team_id')
    def _onchange_user_id(self):
        user_list = []
        user = self.env['maintenance.team'].search([('member_ids', 'in', self.env.uid)], limit=1).id
        if self.maintenance_team_id.member_ids:
            for team in self.maintenance_team_id.member_ids:
                user_list.append(team.id)
            return {'domain': {'user_id': [('id', 'in', tuple(user_list))]}}
        else:
            return []

    @api.onchange('maintenance_team_id')
    def onchange_maintenance_team_id(self):
        if self.maintenance_team_id:
            if self.maintenance_team_id.member_ids:
                self.user_id = self.maintenance_team_id.member_ids.ids[0]

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            code = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                'maintenance.request.code')
            vals['code'] = code
        else:
            code = self.env['ir.sequence'].next_by_code('maintenance.request.code')
            vals['code'] = code

        if not self._context.get('from_web_view'):
            if vals.get('driver_id'):
                employee = self.env['hr.employee'].browse(vals['driver_id'])
                if employee:
                    vals['company_id'] = employee.company_id.id or False
                    vals['branch_id'] = employee.branch_id.id or False
                    calendar = employee.contract_id and employee.contract_id.resource_calendar_id or employee.resource_calendar_id
                    tz = timezone(calendar.tz or 'Asia/Yangon')

                    if vals.get('start_date'):
                        vals['start_date'] = get_utc_datetime(tz, vals.get('start_date'))

                    if vals.get('end_date'):
                        vals['end_date'] = get_utc_datetime(tz, vals.get('end_date'))

        return super(MaintenanceRequest, self).create(vals)

    def send_one_signal_notification(self):
        vehicles = self.env['fleet.vehicle'].sudo().search([])
        if vehicles:
            for vehicle in vehicles:
                reminders = self.env['preventive.reminder'].sudo().search([('vehicle_id', '=', vehicle.id)])
                if reminders:
                    for reminder in reminders:
                        if reminder.next_odometer == vehicle.trip_odometer:
                            if vehicle.hr_driver_id:
                                one_signal_values = {'employee_id': vehicle.hr_driver_id.id,
                                                     'contents': _('%s need to make on %s.') % (
                                                     reminder.name, reminder.next_odometer),
                                                     'headings': _('WB B2B : PREVENTIVE REMINDER')}
                                self.env['one.signal.notification.message'].create(one_signal_values)
                            if vehicle.incharge_id:
                                one_signal_values = {'employee_id': vehicle.incharge_id.id,
                                                     'contents': _('%s need to make on %s.') % (
                                                     reminder.name, reminder.next_odometer),
                                                     'headings': _('WB B2B : PREVENTIVE REMINDER')}
                                self.env['one.signal.notification.message'].create(one_signal_values)
                            if vehicle.hr_manager_id:
                                one_signal_values = {'employee_id': vehicle.hr_manager_id.id,
                                                     'contents': _('%s need to make on %s.') % (
                                                     reminder.name, reminder.next_odometer),
                                                     'headings': _('WB B2B : PREVENTIVE REMINDER')}
                                self.env['one.signal.notification.message'].create(one_signal_values)


class Purchase(models.Model):
    _inherit = 'purchase.order'

    line_id = fields.Many2one('maintenance.request', string='Purchase Show Reference', required=False,
                              ondelete='cascade', index=True, copy=False, auto_join=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=False, store=True)

    def button_confirm(self):
        if self.order_line and self.line_id or self.vehicle_id:
            branch_id = self.line_id.branch_id or self.branch_id
            vehicle_id = self.line_id.vehicle_id or self.vehicle_id
            analytic_tag_obj = self.env['account.analytic.tag']
            for line in self.order_line:
                analyst_list = []
                if branch_id:
                    line.account_analytic_id = branch_id.analytic_account_id
                if vehicle_id:
                    vehicle_license_tag = analytic_tag_obj.sudo().search([('name', '=', vehicle_id.license_plate),
                                                                          ('branch_id', '=', branch_id.id),
                                                                          ('company_id', '=', self.company_id.id)])
                    if vehicle_license_tag:
                        analyst_list.append(vehicle_license_tag)
                    for tag in vehicle_id.tag_ids:
                        analytic_tag = analytic_tag_obj.sudo().search([('name', '=', tag.name),
                                                                       ('company_id', '=', self.company_id.id),
                                                                       ('branch_id', '=', branch_id.id)])
                        if analytic_tag:
                            analyst_list.append(analytic_tag)
                    line.analytic_tag_ids = [(6, 0, [x.id for x in analyst_list])]
        return super(Purchase, self).button_confirm()

    def action_view_invoice(self):

        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.read()[0]
        create_bill = self.env.context.get('create_bill', False)
        result['context'] = {
            'default_type': 'in_invoice',
            'default_company_id': self.company_id.id,
            'default_purchase_id': self.id,
            'default_partner_id': self.partner_id.id,
        }

        self.sudo()._read(['invoice_ids'])
        if len(self.invoice_ids) > 1 and not create_bill:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        else:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                result['views'] = form_view
            if not create_bill:
                result['res_id'] = self.invoice_ids.id or False
        result['context']['default_invoice_origin'] = self.name
        result['context']['default_ref'] = self.partner_ref
        result['context']['default_source_doc'] = self.line_id.code
        result['context']['default_loan_ref'] = self.loan_id.name
        return result

    @api.constrains('order_line')
    def _constrains_order_line(self):
        if self.order_line and self.line_id or self.vehicle_id:
            branch_id = self.line_id.branch_id or self.branch_id
            vehicle_id = self.line_id.vehicle_id or self.vehicle_id
            analytic_tag_obj = self.env['account.analytic.tag']
            for line in self.order_line:
                analyst_list = []
                if branch_id:
                    line.account_analytic_id = branch_id.analytic_account_id
                if vehicle_id:
                    vehicle_license_tag = analytic_tag_obj.sudo().search([('name', '=', vehicle_id.license_plate),
                                                                          ('branch_id', '=', branch_id.id),
                                                                          ('company_id', '=', self.company_id.id)])
                    if vehicle_license_tag:
                        analyst_list.append(vehicle_license_tag)
                    for tag in vehicle_id.tag_ids:
                        analytic_tag = analytic_tag_obj.sudo().search([('name', '=', tag.name),
                                                                       ('company_id', '=', self.company_id.id),
                                                                       ('branch_id', '=', branch_id.id)])
                        if analytic_tag:
                            analyst_list.append(analytic_tag)
                    line.analytic_tag_ids = [(6, 0, [x.id for x in analyst_list])]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # def _prepare_account_move_line(self, move):
    #     self.ensure_one()
    #     if self.product_id.purchase_method == 'purchase':
    #         qty = self.product_qty - self.qty_invoiced
    #     else:
    #         qty = self.qty_received - self.qty_invoiced
    #     if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) <= 0:
    #         qty = 0.0

    #     if self.currency_id == move.company_id.currency_id:
    #         currency = False
    #     else:
    #         currency = move.currency_id

    #     analyst_list = []
    #     if self.order_id.line_id.vehicle_id:
    #         company_id = self.order_id.line_id.vehicle_id.company_id
    #         branch_id = self.order_id.line_id.vehicle_id.branch_id
    #         for tag in self.order_id.line_id.vehicle_id.tag_ids:
    #             analytic_tag = self.env['account.analytic.tag'].sudo().search([('name', '=', tag.name),
    #                                                                     ('company_id', '=', company_id.id),
    #                                                                     ('branch_id', '=', branch_id.id)])
    #             if analytic_tag:
    #                 analyst_list.append(analytic_tag.id)
    #     return {
    #         'name': '%s: %s' % (self.order_id.name, self.name),
    #         'move_id': move.id,
    #         'currency_id': currency and currency.id or False,
    #         'purchase_line_id': self.id,
    #         'date_maturity': move.invoice_date_due,
    #         'product_uom_id': self.product_uom.id,
    #         'product_id': self.product_id.id,
    #         'price_unit': self.price_unit,
    #         'quantity': qty,
    #         'partner_id': move.partner_id.id,
    #         'analytic_account_id': self.account_analytic_id.id,
    #         'analytic_tag_ids': [(6, 0, analyst_list)],
    #         'tax_ids': [(6, 0, self.taxes_id.ids)],
    #         'display_type': self.display_type,
    #     }


class WarehouseIssue(models.Model):
    _name = 'warehouse.issue'
    _description = 'Warehouse Issue'

    line_id = fields.Many2one('maintenance.request', string='Maintenance Request ID', required=False,
                              ondelete='cascade', index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', related='line_id.company_id')
    location_id = fields.Many2one('stock.location', string='Location')
    qty = fields.Float(string='Quantity')
    product_id = fields.Many2one('product.product', string='Product')
    cost = fields.Float(string='Cost', related='product_id.standard_price')


class MaintenanceProduct(models.Model):
    _name = 'maintenance.product'
    _description = 'Maintenance Product'

    category_id = fields.Many2one('product.category', string='Product Category',
                                  domain="['|',('maintenance', '=', True),('preventive','=', True)]")
    product_id = fields.Many2one('product.product', string='Product')
    type = fields.Selection([('repair', 'Repair'), ('new', 'New')], string='Type')
    qty = fields.Float(string='Quantity')
    line_id = fields.Many2one('maintenance.request', string='Maintenance Request ID', required=False,
                              ondelete='cascade', index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', related='line_id.company_id')

    @api.onchange('category_id')
    def onchange_product_category(self):
        domain = {}
        if not self.category_id:
            domain['product_id'] = ['|', ('product_tmpl_id.company_id', '=', False),
                                    ('product_tmpl_id.company_id', '=', self.line_id.company_id.id)]
        else:
            domain['product_id'] = [('product_tmpl_id.categ_id', '=', self.category_id.id), '|',
                                    ('product_tmpl_id.company_id', '=', False),
                                    ('product_tmpl_id.company_id', '=', self.line_id.company_id.id)]
        return {'domain': domain}


class Fleet(models.Model):
    _inherit = 'fleet.vehicle'

    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")
    incharge_id = fields.Many2one('hr.employee', string="Incharge", required=True,
                                  domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")
    spare_id = fields.Many2one('hr.employee', string="Spare",
                               domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")
    maintenance_count = fields.Integer(compute="_compute_maintenance_count", string='Maintenance')

    def _compute_maintenance_count(self):
        self.maintenance_count = self.env['maintenance.request'].search_count([('vehicle_id', '=', self.id)])


class FleetServiceType(models.Model):
    _name = 'maintenance.type'
    _description = 'Maintenance Type'

    name = fields.Char(required=True, translate=True)


class MaintenanceTeam(models.Model):
    _inherit = 'maintenance.team'
    _description = 'Maintenance Teams'

    contact_no = fields.Char(string='Contact No')
    address = fields.Char(string='Address')
    partner_id = fields.Many2one('res.partner', string='Partner')

    def name_get(self):
        result = []
        for record in self:
            if record.name and record.address and record.contact_no:
                result.append((record.id, record.name + '/' + record.address + '/' + record.contact_no))
            if record.name and record.address and not record.contact_no:
                result.append((record.id, record.name + '/' + record.address))
            if record.name and record.contact_no and not record.address:
                result.append((record.id, record.name + '/' + record.contact_no))
            if record.name and not record.address and not record.contact_no:
                result.append((record.id, record.name))
        return result


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = 'Stock Picking'

    maintenance_request_id = fields.Many2one('maintenance.request', string='Maintenance Request')

    # def button_validate(self):
    #     res = super(StockPicking, self).button_validate()
    #     invoice_obj = self.env['account.move']
    #     misc_journal = self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('short_code', '=', 'MISC')], limit=1)
    #     print("####", misc_journal.id)
    #     move_dict = {
    #         'narration': '',
    #         'ref': self.code,
    #         'type' : 'out_invoice',
    #         'date': date.today(),
    #         'journal_id' : misc_journal.id,
    #     }
    #     debit_account = product_id.property_account_expense_id
    #     credit_account =

    #     line_ids = []
    #     if debit_account:
    #         debit = driver_amount if driver_amount > 0.0 else 0.0
    #         credit = -driver_amount if driver_amount < 0.0 else 0.0
    #         debit_line = {
    #             'account_id': debit_account_id,
    #             'journal_id': self.journal_id.id,
    #             'date': date.today(),
    #             'debit': debit,
    #             'credit': credit,
    #             'exclude_from_invoice_tab': True
    #         }
    #         line_ids.append(debit_line)
    #     if credit_account:
    #         debit = -driver_amount if driver_amount < 0.0 else 0.0
    #         credit = driver_amount if driver_amount > 0.0 else 0.0
    #         credit_line = {
    #             'account_id': driver_credit_account_id,
    #             'journal_id': self.journal_id.id,
    #             'date': date.today(),
    #             'debit': debit,
    #             'credit': credit,
    #             'exclude_from_invoice_tab': True
    #         }
    #         line_ids.append(credit_line)

    #     move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
    #     move = self.env['account.move'].create(move_dict)
    #     self.write({'move_id': move.id})
    #     return res


class StockMove(models.Model):
    _inherit = 'stock.move'
    _description = 'Stock Move'

    maintenance_line_id = fields.Many2one('warehouse.issue')
