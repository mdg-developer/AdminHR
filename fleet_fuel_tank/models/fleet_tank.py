# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import api, fields, models, tools, _
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class fuel_tank(models.Model):
	
	_name = 'fuel.tank'

	def _filling_fuel_percentage(self):
		total_percentage = 0.0
		for record in self:
			capacity = record.capacity
			liters = record.liters
			if capacity != 0.0:
				total_percentage = (liters * 100)/capacity
				per_list = str(total_percentage).split('.')
				ans = per_list[0] +'.'+ per_list[1][:2]
				record.percentage_fuel = ans + ' %'
			else:
				record.percentage_fuel = '0 %'
		
	name = fields.Char('Name',required=True)
	capacity = fields.Float('Capacity')
	location = fields.Char('Location')
	last_clean_date = fields.Date('Last Clean Date')
	liters = fields.Float('Liters', compute='_compute_fuel_tank_liter', readonly=True)
	average_price = fields.Float('Average Price',readonly=True,default=0.0)
	last_filling_date = fields.Date('Last Filling Date',readonly=True)
	last_filling_amount = fields.Float('Last Filling Amount',readonly=True,default=0.0)
	last_filling_price_liter = fields.Float('Last Filling Price',readonly=True,default=0.0)
	fule_filling_history_ids = fields.One2many('fuel.filling.history', 'fuel_filling_id', 'History Lines', readonly=True)
	percentage_fuel = fields.Char(compute = '_filling_fuel_percentage', string='Total Filling Fuel')
	last_fuel_adding_date =fields.Date('Last Added Fuel Date',readonly=True)
	price_unit = fields.Float(string="Unit Price", compute='_compute_fuel_tank_unit_price')
	active = fields.Boolean(default=True, help="The active field allows you to hide the category without removing it.")

	@api.depends('fule_filling_history_ids')
	def _compute_fuel_tank_liter(self):
		for rec in self:
			total_liter = 0
			for line in rec.fule_filling_history_ids:
				total_liter += line.fuel_liter
			rec.liters = total_liter
	
	@api.depends('fule_filling_history_ids.amount', 'fule_filling_history_ids.fuel_liter')
	def _compute_fuel_tank_unit_price(self):
		for rec in self:
			price_unit = 0 
			amount = 0 
			liter = 0
			for line in rec.fule_filling_history_ids:
				amount += line.amount
				liter += line.fuel_liter
			if liter != 0:
				price_unit = amount / liter
			rec.price_unit = price_unit
		

class fleet_vehicle_log_fuel(models.Model):
	_inherit = 'fleet.vehicle.log.fuel'

	def unlink(self):
		for fuel_id in self:
			fuel_tank_id = fuel_id.fuel_tank_id.id
			liters = fuel_id.liter
			fuel_tank_obj = self.env['fuel.tank']
			if fuel_tank_id:
				tank_liters = fuel_tank_obj.browse(fuel_tank_id).liters
				total_liters = tank_liters + liters
				fuel_tank_obj.browse(fuel_tank_id).write({'liters':total_liters})
		super(fleet_vehicle_log_fuel, self).unlink()

	@api.onchange('fuel_tank_id')
	def onchange_fuel_tank(self):
		res = {}
		if self.fuel_tank_id:
			res['price_per_liter'] = self.fuel_tank_id.average_price
		return {'value': res}

	fuel_tank_id = fields.Many2one('fuel.tank','Fuel Tank',required=True, related='vehicle_id.fuel_tank', readonly=False)
	employee_id = fields.Many2one('hr.employee','Employee',required=True, default=lambda self: self.env['hr.employee'].search([], limit=1))
	previous_odometer = fields.Float('Previous Odometer Reading',readonly=True, default=0.0)
	prev_odo = fields.Float('Prev Odo Reading', default=0.0)
	shop = fields.Char('Shop')
	source_doc = fields.Char(string='Source Doc')

	def _check_odometer(self):
		if self.odometer < self.previous_odometer:
			return False
		return True

	_constraints = [
		(_check_odometer, 'Odometer value should be greater than Previous Odometer Reading', ['previous_odometer']),
	]

	@api.onchange('vehicle_id')
	def onchange_vehicle(self):
		val = {}
		if self.vehicle_id:
			vehicle_ids  = self.search([('vehicle_id','=',self.vehicle_id.id)])
			if vehicle_ids:
				vehicle_max_id = max(vehicle_ids)
				if vehicle_max_id:
					prev_odometer = vehicle_max_id.read(['odometer'])[0].get('odometer')
					val = {
							'previous_odometer': prev_odometer,
							'prev_odo': prev_odometer,
						}
			else:
				val = {
						'previous_odometer': 0.0,
						'prev_odo': 0.0,
					}
		return {'value': val}


	@api.model
	def create(self,vals):
		log_id = self.search([('vehicle_id','=',vals.get('vehicle_id'))])
		odometer_forward = 0.0
		if log_id:
			odometer_forward = max(log_id).odometer
		else:
			odometer_forward = 0.0

		date = datetime.now()
		defaultdate =  date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		filldate = defaultdate.split()[0]
		hr_employee_obj=self.env['hr.employee']
		fuel_tnk_obj=self.env['fuel.tank']
		system_date = filldate
		odo_fuel_obj = self.env['odometer.filling.history']
		vehicle_obj = self.env['fleet.vehicle']
		fuel_tank_id = vals.get('fuel_tank_id',False)
		employee_id = vals.get('employee_id',False)
		if employee_id:
			employee = hr_employee_obj.browse(employee_id)
		vehicle_id = vals.get('vehicle_id',False)
		if vehicle_id:
			vehicle = vehicle_obj.browse(vehicle_id)
		liters = vals.get('liter',0.0)
		price_per_liter = vals.get('price_per_liter',0.0)
		odometer_latest = vals.get('odometer',0.0)
		previous_odometer = vals.get('prev_odo',0.0)

		fuel_litter = vals.get('liter',0.0)
		fuel_tan = vals.get('fuel_tank_id')
		fuel_tan_liter = fuel_tnk_obj.browse(fuel_tan).liters
		# if fuel_litter >= fuel_tan_liter:
		# 	raise UserError(_('Liter value should be greater than previous Fual tank value!'))
			
		if previous_odometer:
			vals.update({'previous_odometer': previous_odometer})
		odometer_final = odometer_latest - odometer_forward
		# if previous_odometer >= odometer_latest:
		# 	raise UserError(_('Odometer value should be greater than previous odometer value!'))
			
		great_average_obj = self.env['compsuption.great.average']
		consuption_average = 0.0
		log_id = super(fleet_vehicle_log_fuel, self).create(vals)
		# if odometer_final != 0.0:
		# 	consuption_average = ((liters/odometer_final)*100)
		# 	great_average_obj.create({'great_average':consuption_average,'vehicle_id':vehicle_id, 'employee_id':employee_id,'consumption_average_id': log_id.id, 'modified_date': system_date})
		odometer_vals = {
			'fuel_liter':liters,
			'price_per_liter':price_per_liter,
			'filling_date':system_date,
			'fuel_filling_odometer_id': fuel_tank_id,
		}
		odo_fuel_obj.create(odometer_vals)
		amount = vals.get('amount',0.0)
		fuel_tank_obj = self.env['fuel.tank']
		ft_liters = fuel_tank_obj.browse(fuel_tank_id).liters
		final_liters = ft_liters - liters
		great_con_ids = great_average_obj.search([('vehicle_id','=',vehicle_id)])
		self.sub_great_avg = 0.0
		self.final_great_avg = 0.0
		self.index = 0
		if len(great_con_ids) > 0:
			for great_id in great_con_ids:
				self.index += 1
				greate_conm_avg = great_id.great_average
				self.sub_great_avg += greate_conm_avg
			self.final_great_avg = self.sub_great_avg / self.index
		res = {
			'liters':final_liters,
			'last_filling_price_liter':price_per_liter,
			'last_filling_amount':amount,
			'last_filling_date':system_date,
		}
		res_vehicle = {
			'consuption_average':consuption_average,
		}
		fuel_tank_obj.browse(fuel_tank_id).write(res)
		vehicle_obj.browse(vehicle_id).write(res_vehicle)
		return log_id

	def write(self, vals):
		liters = 0.0
		price_per_liter = 0.0
		fuel_tank_obj = self.env['fuel.tank']
		if vals.get('odometer'):
			previous_odometer = self.previous_odometer or 0.0
			# if previous_odometer >= vals.get('odometer'):
			# 	raise UserError(_('Odometer value should be greater than previous odometer value!'))
				
		if self.fuel_tank_id:
			ft_liters = self.fuel_tank_id.liters
			if vals.get('liter'):
				liters = vals.get('liter')
		ft_liters = fuel_tank_obj.browse(self.fuel_tank_id.id).liters
		liters = vals.get('liter')

		fuel_litter = vals.get('liter',0.0)
		fuel_tan = vals.get('fuel_tank_id',False)
		fuel_tan_liter = fuel_tank_obj.browse(fuel_tan).liters
		# if fuel_litter >= fuel_tan_liter:
		# 	raise UserError(_('Liter value should be greater than previous Fual tank value!"'))
		   
		if liters:
			final_liters = ft_liters - liters
			if vals.get('price_per_liter'):
				price_per_liter = vals.get('price_per_liter') or 0.0
			amount = liters * price_per_liter
			system_date = time.strftime("%d-%m-%Y")
			old_liters = self.liter
			ft_liters = fuel_tank_obj.browse(self.tank_id.id).liters
			ft_liters_updated = 0.0
			if old_liters > liters:
				difference_litter = old_liters - liters
				ft_liters_updated = ft_liters + difference_litter
			if liters > old_liters:
				difference_litter = liters - old_liters
				ft_liters_updated = ft_liters - difference_litter
			res = {
				'liters':ft_liters_updated,
				'last_filling_price_liter':price_per_liter,
				'last_filling_amount':amount,
				'last_filling_date':system_date,
			}
			fuel_tank_obj.write(self.tank_id.id,res)
		return super(fleet_vehicle_log_fuel, self).write(vals)

class fleet_vehicle(models.Model):
	_inherit = 'fleet.vehicle'
	
	consuption_average = fields.Float("Consumption Average",readonly=True)
	grant_consuption_average = fields.Float(compute='_get_grant_consuption_average',  string='Grand Consumption Average',store=True)
	consumption_average_history_ids = fields.One2many('compsuption.great.average', 'vehicle_id', 'Consumption History', readonly=True)
	fuel_tank = fields.Many2one('fuel.tank','Fuel Tank')
	fleet_tyre_history_ids = fields.One2many('fleet.tyre.history', 'vehicle_id', 'Tyre History')

	def _get_grant_consuption_average(self):
		val = 0.0
		res = {}
		for vehicle in self:
			counter = 0
			val = 0.0
			if vehicle.consumption_average_history_ids:
				for line in vehicle.consumption_average_history_ids:
					val += line.great_average
					counter += 1
				res[vehicle.id] = val/counter
			else:
				res[vehicle.id] = 0.0
		return res
	
	def action_open_fuel_consumption(self):
		self.ensure_one()
		xml_id = self.env.context.get('xml_id')
		if xml_id:
			res = self.env['ir.actions.act_window'].for_xml_id('fleet_fuel_tank', xml_id)
			res.update(
				context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
				domain=[('vehicle_id', '=', self.id)]
			)
			return res
		return False
	
	def action_open_accounting_config(self):
		self.ensure_one()
		xml_id = self.env.context.get('xml_id')
		if xml_id:
			res = self.env['ir.actions.act_window'].for_xml_id('fleet_fuel_tank', xml_id)
			res.update(
				context=dict(self.env.context, default_vehicle_id=self.id, default_company_id=self.company_id.id, group_by=False),
				domain=[('vehicle_id', '=', self.id)]
			)
			return res
		return False
	
	def action_open_preventive_reminder(self):
		self.ensure_one()
		xml_id = self.env.context.get('xml_id')
		if xml_id:
			res = self.env['ir.actions.act_window'].for_xml_id('fleet_fuel_tank', xml_id)
			res.update(
				context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
				domain=[('vehicle_id', '=', self.id)]
			)
			return res
		return False
	

class FuelFillingHistory(models.Model):
	_name = 'fuel.filling.history'

	fuel_liter = fields.Float('Liters',readonly=False)
	price_per_liter = fields.Float('Unit Price',readonly=False)
	filling_date = fields.Date('Date',readonly=False)
	source_doc = fields.Char(string='Source Doc')
	fuel_filling_id = fields.Many2one('fuel.tank','Fuel Filling Reference', ondelete='cascade')
	amount = fields.Float(string='Amount', compute='compute_amount')

	@api.depends('fuel_liter', 'price_per_liter')
	def compute_amount(self):
		for rec in self:
			rec.amount = 0
			if rec.fuel_liter and rec.price_per_liter:
				rec.amount = rec.fuel_liter * rec.price_per_liter
				

class OdometerFillingHistory(models.Model):
	_name = 'odometer.filling.history'

	fuel_liter = fields.Float('Liters')
	price_per_liter = fields.Float('Price')
	filling_date = fields.Date('Date')
	fuel_filling_odometer_id = fields.Many2one('fuel.tank','Fuel Filling Reference', ondelete='cascade')


class compsuption_great_average(models.Model):
	_name = 'compsuption.great.average'
	
	name = fields.Char('Name', readonly=True)
	great_average = fields.Float('Consumption Rate', compute='_compute_consumption_average')
	vehicle_id = fields.Many2one('fleet.vehicle',"Vehicle")
	consumption_average_id = fields.Many2one('fleet.vehicle.log.fuel','Consumption Average', select=True, ondelete='cascade')
	modified_date = fields.Date('Filling Date')
	employee_id = fields.Many2one('hr.employee','Employee')
	consumption_liter = fields.Float('Consumption Liter')
	source_doc = fields.Char('Source Doc')
	odometer = fields.Float(string='Current Odometer')
	last_odometer = fields.Float(string='Last Odometer')
	travel_odometer = fields.Float(string='Travel Odometer', compute='_compute_travel_odometer', store=True)

	@api.depends('travel_odometer', 'consumption_liter')
	def _compute_consumption_average(self):
		for rec in self:
			rec.great_average = 0
			if rec.consumption_liter != 0 and rec.travel_odometer != 0:
				rec.great_average = rec.travel_odometer / rec.consumption_liter
	
	@api.depends('odometer', 'last_odometer')
	def _compute_travel_odometer(self):
		for rec in self:
			rec.travel_odometer = rec.odometer - rec.last_odometer

	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('fuel.consumption.code')
		return super(compsuption_great_average, self).create(vals)


class FleetAccountingConfig(models.Model):
	_name = 'fleet.accounting.config'
	_rec_name = 'journal_id'
	
	vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
	company_id = fields.Many2one('res.company', string='Company')
	journal_id = fields.Many2one('account.journal', string='Journal')
	operation_journal_id = fields.Many2one('account.journal', string='Operation Journal')
	analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag')
		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
