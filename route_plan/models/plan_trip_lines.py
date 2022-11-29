from odoo import api, fields, models, _


class TripRouteLine(models.Model):
    _name = 'trip.route.line'
    _description = 'Plan Trip Waybill Routes'

    company_id = fields.Many2one('res.company', string='Company')
    route_id = fields.Many2one('route.plan', string='Route', domain=[('state', 'in', ('approve', 'verify'))], required=True)
    trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill', ondelete='cascade', index=True)
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)


class TripExpense(models.Model):
    _name = 'trip.expense'
    _description = 'Trip Expense'

    route_id = fields.Many2one('route.plan', string='Route', domain=[('state', 'in', ('approve', 'verify'))])
    route_expense_id = fields.Many2one('route.expense', string='Route Expense', required=True)
    product_id = fields.Many2one('product.product', string='Expense', related='route_expense_id.product_id')
    standard_amount = fields.Float(related='route_expense_id.amount', string='Standard Amount')
    actual_amount = fields.Float('Actual Amount')
    over_amount = fields.Float(string='Over Amount', compute='compute_over_amount')
    description = fields.Char(string='Description')
    is_required = fields.Boolean(string='Is Required?', compute='compute_is_required')
    trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill', ondelete='cascade', index=True)
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)
    log_user_id = fields.Many2one('res.users', string="Created User")
    attached_file = fields.Binary(string='Attachment')
    create_emp_id = fields.Many2one('hr.employee', string='Created Employee', store=True, readonly=True)
    update_emp_id = fields.Many2one('hr.employee', string='Updated Employee', store=True, readonly=True)
    
    @api.onchange('attached_file','description','actual_amount')
    def onchange_product(self):
        self.log_user_id = self.env.user.id
        update_emp = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        if update_emp:
            self.update_emp_id = update_emp.id
    
    @api.depends('standard_amount', 'actual_amount')
    def compute_is_required(self):
        for rec in self:
            if rec.actual_amount > rec.standard_amount:
                rec.is_required = True
            else:
                rec.is_required = False
    
    @api.depends('standard_amount', 'actual_amount')
    def compute_over_amount(self):
        for rec in self:
            rec.over_amount = rec.actual_amount - rec.standard_amount
                

class TripFuelConsumption(models.Model):
    _name = 'trip.fuel.consumption'
    _description = 'Fuel Consumption'

    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
    route_id = fields.Many2one('route.plan', string='Route', required=False)
    standard_liter = fields.Integer('Standard Consumption (Liter)', related='route_id.fuel_liter')
    consumed_liter = fields.Float('Actual Consumption (Liter)', required=True)
    trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill', ondelete='cascade', index=True)
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)
    day_trip_id = fields.Many2one('day.plan.trip', string='Day Plan Trip', ondelete='cascade', index=True)
    last_odometer = fields.Float(string='Last Odometer')
    current_odometer = fields.Float(string='Current Odometer')
    trip_distance = fields.Float(string='Trip Distance', compute='_compute_trip_distance')
    avg_calculation = fields.Float(string='Avg', compute='_compute_avg_calculation')
    description = fields.Char(string='Description')
    is_required = fields.Boolean(string='Is Required?', compute='compute_is_required')
    date = fields.Datetime(string='Date')

    @api.depends('consumed_liter', 'standard_liter')
    def compute_is_required(self):
        for rec in self:
            if rec.consumed_liter > rec.standard_liter:
                rec.is_required = True
            else:
                rec.is_required = False

    @api.depends('last_odometer', 'current_odometer')
    def _compute_trip_distance(self):
        for record in self:
            record.trip_distance = record.current_odometer - record.last_odometer
    
    @api.depends('trip_distance', 'consumed_liter')
    def _compute_avg_calculation(self):
        for record in self:
            consumed_liter = float(record.consumed_liter)
            trip_distance = float(record.trip_distance)
            if consumed_liter != 0.0:
                record.avg_calculation = trip_distance / consumed_liter
            else:
                record.avg_calculation = 0.0
    
    def unlink(self):
        res = super(TripFuelConsumption, self).unlink()
        for rec in self:
            consumption_history = self.env['compsuption.great.average'].sudo().search([('trip_consumption_line_id', '=', rec.id)])
            fuel_tank_filling_history = self.env['fuel.filling.history'].sudo().search([('trip_consumption_line_id', '=', rec.id)])
            if consumption_history:
                consumption_history.unlink()
            if fuel_tank_filling_history:
                fuel_tank_filling_history.unlink()
        return res



class TripCommission(models.Model):
    _name = 'trip.commission'
    _description = 'Trip Commission'

    route_id = fields.Many2one('route.plan', string='Route', domain=[('state', 'in', ('approve', 'verify'))], required=True)
    commission_driver = fields.Integer('Commission (Driver)', related='route_id.commission_driver')
    commission_spare = fields.Integer('Commission (Spare)', related='route_id.commission_spare')
    trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill', ondelete='cascade', index=True)


class TripFuelIn(models.Model):
    _name = 'trip.fuel.in'
    _description = 'Fuel In'
    
    company_id = fields.Many2one('res.company', string='Company')
    product_id = fields.Many2one('product.product', string='Product')
    date = fields.Date('Date', required=True)
    shop = fields.Char('Shop')
    liter = fields.Float('Liter', default=1)
    price_unit = fields.Float('Price', default=1, compute='_compute_price_unit', readonly=False, store=True)
    amount = fields.Float('Amount', compute='_compute_amount', readonly=False, store=True)
    trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill', ondelete='cascade', index=True)
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)
    day_trip_id = fields.Many2one('day.plan.trip', string='Day Plan Trip', ondelete='cascade', index=True)
    location_id = fields.Many2one('stock.location', 'Location')
    slip_no = fields.Char(string='Slip No')
    add_from_office = fields.Boolean(string='Added From Office?', default=False)
    
    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.price_unit = self.product_id.product_tmpl_id.standard_price

    @api.depends('liter', 'price_unit')
    def _compute_amount(self):
        for record in self:
            record.amount = record.price_unit * record.liter
    
    @api.depends('liter', 'amount')
    def _compute_price_unit(self):
        for record in self:
            record.price_unit = record.amount / record.liter
    
    def unlink(self):
        res = super(TripFuelIn, self).unlink()
        for rec in self:
            fuel_logs = self.env['fleet.vehicle.log.fuel'].sudo().search([('trip_fuel_in_line_id', '=', rec.id)])
            fuel_tank_filling_history = self.env['fuel.filling.history'].sudo().search([('trip_fuel_in_line_id', '=', rec.id)])
            vehicle_costs = self.env['fleet.vehicle.cost'].sudo().search([('trip_fuel_in_line_id', '=', rec.id)])
            if fuel_logs:
                fuel_logs.unlink()
            if fuel_tank_filling_history:
                fuel_tank_filling_history.unlink()
            if vehicle_costs:
                vehicle_costs.unlink()
        return res


class TripAdvance(models.Model):
    _name = 'trip.advance'
    _description = 'Trip Advance'

    route_id = fields.Many2one('route.plan', string='Route', domain=[('state', 'in', ('approve', 'verify'))], required=True)
    approved_advance = fields.Float('Approved Advance', related='route_id.approved_advance')
    trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill', ondelete='cascade', index=True)
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)


class TripProductLine(models.Model):
    _name = 'trip.product.line'
    _description = 'Trip Product'

    company_id = fields.Many2one('res.company', string='Company')
    product_id = fields.Many2one('product.product', string='Name',domain=[('product_tmpl_id.categ_id.delivery', '=', True)])
    name = fields.Char('Description')
    product_uom = fields.Many2one('uom.uom', string='UOM', related='product_id.uom_id')
    quantity = fields.Float('Quantity', default=1)
    price_unit = fields.Float('Price', default=1)
    amount = fields.Float('Amount', compute='_compute_amount')
    trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product', ondelete='cascade', index=True)
    day_trip_id = fields.Many2one('day.plan.trip', string='Day Plan Trip', ondelete='cascade', index=True)

    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for record in self:
            record.amount = record.price_unit * record.quantity


class DayTripExpense(models.Model):
    _name = 'day.trip.expense'
    _description = 'Day Trip Expense'

    company_id = fields.Many2one('res.company', string='Company')
    product_id = fields.Many2one('product.product', string='Expense', domain=[('product_tmpl_id.categ_id.day_trip', '=', True)])
    name = fields.Char(string='Description')
    amount = fields.Float(string='Amount')
    day_trip_id = fields.Many2one('day.plan.trip', string='Day Plan Trip', ondelete='cascade', index=True)
    attached_file = fields.Binary(string='Attachment')
    create_emp_id = fields.Many2one('hr.employee', string='Created Employee', store=True, readonly=True)
    update_emp_id = fields.Many2one('hr.employee', string='Updated Employee', store=True, readonly=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name

    @api.onchange('name', 'amount', 'attached_file')
    def onchange_expense_line(self):
        if self.name or self.amount or self.attached_file:
            update_emp = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            if update_emp:
                self.update_emp_id = update_emp.id