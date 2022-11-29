# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class Task(models.Model):
	_inherit = "project.task"

	custom_application_id = fields.Many2one(
		'emp.training.application',
		string='Application',
		copy=False
	)
	# subject_id = fields.Many2one(
	# 	'training.subject',
	# 	string='Subject',
	# 	copy=False
	# )
	custom_subject_id = fields.Many2one(
		'slide.slide',
		string='Subject',
		copy=False
	)
	custom_application_line_id = fields.Many2one(
		'emp.training.application.line',
		string='Application Line',
		copy=False
	)
	custom_training_start_date = fields.Date(
		string='Training Start Date',
		copy=False
	)
	custom_training_end_date = fields.Date(
		string='Training End Date',
		copy=False
	)
	custom_training_employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
		copy=False
	)
	custom_is_application_task = fields.Boolean(
		string='Is Application Task?',
	)
	training_hour = fields.Char(
		string='Training Hr',
		required=False
	)
	training_type_id = fields.Many2one(
		'emp.training.type',
		string='Training Type'
	)

	company_id = fields.Many2one('res.company',string="Company")
	branch_id = fields.Many2one('res.branch', related='custom_training_employee_id.branch_id', store=True,
								string='Branch',
								readonly=True)
	department_id = fields.Many2one('hr.department', related='custom_training_employee_id.department_id', store=True,
									string='Department',
									readonly=True)
	position = fields.Many2one('hr.job',string="Position")

	@api.onchange('custom_training_employee_id')
	def onchange_custom_training_employee_id(self):
		# import pdb
		# pdb.set_trace()
		if self.custom_training_employee_id:
			self.write({'company_id':self.custom_training_employee_id.company_id.id,'branch_id':self.custom_training_employee_id.branch_id.id,
						'department_id':self.custom_training_employee_id.department_id.id,'position':self.custom_training_employee_id.job_id})

class Project(models.Model):
	_inherit = "project.project"

	custom_application_count = fields.Integer(
		compute='_compute_application_counter',
		string="Application Count"
	)

	# @api.multi
	def action_application(self):
		action = self.env.ref('odoo_training_management_app.action_training_application').read()[0]
		action['domain'] = [('project_id','in', self.ids)]
		return action

	def _compute_application_counter(self):
		for  rec in self:
			rec.custom_application_count = self.env['emp.training.application'].search_count([('project_id', 'in', self.ids)])
		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: