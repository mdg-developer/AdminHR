# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	custom_task_count = fields.Integer(
		compute='_compute_task_counter',
		string="Task Count"
	)
	custom_application_count = fields.Integer(
		compute='_compute_application_counter',
		string="Application Count"
	)
	# training_application_id = fields.Many2one(
	# 	'emp.training.application', 
	# 	string="Training Application")

	def _compute_task_counter(self):
		for rec in self:
			rec.custom_task_count = self.env['project.task'].search_count([('custom_training_employee_id', 'in', self.ids)])

	def _compute_application_counter(self):
		for rec in self:
			rec.custom_application_count = self.env['emp.training.application'].search_count([('employee_id', 'in', self.ids)])

	# @api.multi
	def action_emp_application(self):
		action = self.env.ref('odoo_training_management_app.action_training_application').read()[0]
		action['domain'] = [('employee_id','in', self.ids)]
		return action

	# @api.multi
	def action_view_employee_task(self):
		action = self.env.ref('odoo_training_management_app.action_view_application_task').read()[0]
		action['domain'] = [('custom_training_employee_id','in',self.ids)]
		return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: