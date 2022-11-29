# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date,datetime,timedelta
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class TrainingApplication(models.Model):
	_name = "emp.training.application"
	_rec_name = 'number'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	

	@api.model
	def _default_stage(self):
		stage_id = self.env['emp.training.application.stage'].search([('default_stage','=', True)],limit=1)
		return stage_id
	
	trainer_id = fields.Many2one(
		'res.partner',
		string='Trainer'
	)
	application_name = fields.Char(
		string='Application Name',
		required=True
	)
	training_name = fields.Char(
		string='Training Name',
		required=True
	)
	description = fields.Text(
		string='Description'
	)
	create_date = fields.Date(
		string='Create Date',
		required=True,
		default=fields.Date.context_today
	)
	company_id = fields.Many2one(
		'res.company',
		string='Company',
		required=True,
		default=lambda self: self.env.user.company_id
	)
	user_id = fields.Many2one(
		'res.users',
		string='Responsible',
		default=lambda self: self.env.user,
		required=True
	)
	employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
		required=False
	)
	employee_ids = fields.Many2many(
		'hr.employee', 
		string='Employee'
	)
	stage_id = fields.Many2one(
		'emp.training.application.stage',
		string='Stage',
		track_visibility='onchange',
		default=_default_stage,
		index=True
	)
	application_line_ids = fields.One2many(
		'emp.training.application.line',
		'application_id', 
		string='Application Line'
	)
	project_id = fields.Many2one(
		'project.project',
		string='Project'
	)
	number = fields.Char(
		string='Number',
		readonly=True,
		copy=False
	)
	start_date = fields.Date(
		string='Start Date',
		required=True
	)
	end_date = fields.Date(
		string='End Date',
		required=True
	)
	is_approve = fields.Boolean(
		string='Is Approved?',
		related = 'stage_id.is_approve',
		store = True
	)
	is_cancel = fields.Boolean(
		string='Is Canceled?',
		related = 'stage_id.is_cancel',
		store = True
	)
	is_draft = fields.Boolean(
		string='Is Draft?',
		related = 'stage_id.is_draft',
	)
	is_task_created = fields.Boolean(
		string='Is Task Created',copy=False,default=False
	)
	task_count = fields.Integer(
		compute='_compute_task_counter',
		string="Task Count"
	)
	training_hour = fields.Char(
		string='Training Hr',
		required=False
	)
	training_type_id = fields.Many2one(
		'emp.training.type',
		string='Training Type'
	)
	type = fields.Selection(
		[('internal', 'Internal'), ('external', 'External')],
		string='Type', default="internal")
	cost_line_ids = fields.One2many(
		'training.cost.line',
		'application_cost_id',
		string='Training Cost Line'
	)

	def _compute_task_counter(self):
		for  rec in self:
			rec.task_count = self.env['project.task'].search_count([('custom_application_id', 'in', self.ids)])

	@api.model
	def create(self, vals):
		vals['number'] = self.env['ir.sequence'].next_by_code('emp.training.application') 
		stage_id = self.env['emp.training.application.stage'].search([('default_stage','=', True)],limit=1)
		if stage_id:
			vals.update({'stage_id': stage_id.id})
		else:
			raise UserError(_('Please Set Default Stage.'))
		return super(TrainingApplication, self).create(vals)

	def write(self, vals):
		stage_ids = self.env['emp.training.application.stage'].search(['|',('is_approve','=',True),('is_cancel','=',True)]).ids
		if 'stage_id' in vals and vals.get('stage_id') in stage_ids:
			if not self.env.user.has_group('odoo_training_management_app.group_training_user') and not self.env.user.has_group('odoo_training_management_app.group_training_manager'):
				raise UserError(_('You can not Change Stage.'))
		return super(TrainingApplication, self).write(vals)

	# @api.multi
	def create_task(self):
		for rec in self:
			# for line in rec.application_line_ids:
			# 	for subject in line.subject_ids:
			# 		vals = {
			# 			'custom_application_id': rec.id,
			# 			'name': rec.number + "-" + rec.application_name,
			# 			'custom_subject_id': subject.id,
			# 			'custom_application_line_id': line.id,
			# 			'custom_training_start_date': line.start_date,
			# 			'custom_training_end_date': line.end_date,
			# 			'project_id': rec.project_id.id,
			# 			'user_id': self.env.user.id,
			# 			'custom_training_employee_id': rec.employee_id.id,
			# 			'date_deadline': line.end_date,
			# 			'description': line.description,
			# 			'custom_is_application_task': True
			# 		}
			# 		task = self.env['project.task'].create(vals)

			for emp in rec.employee_ids:
				for line in rec.application_line_ids:
					for subject in line.subject_ids:
						vals = {
							'custom_application_id': rec.id,
							'name': rec.number + "-" + rec.application_name,
							'custom_subject_id': subject.id,
							'custom_application_line_id': line.id,
							'custom_training_start_date': line.start_date,
							'custom_training_end_date': line.end_date,
							'project_id': rec.project_id.id,
							'user_id': self.env.user.id,
							'company_id': emp.company_id.id,
							'branch_id': emp.branch_id.id,
							'department_id': emp.department_id.id,
							'position': emp.job_id.id,
							'custom_training_employee_id': emp.id,
							'date_deadline': line.end_date,
							'description': line.description,
							'custom_is_application_task': True,
							'training_hour':rec.training_hour or '',
							'training_type_id':rec.training_type_id.id or False,
						}
						task = self.env['project.task'].create(vals)
		rec.is_task_created = True


	# @api.multi
	def view_task_application(self):
		action = self.env.ref('odoo_training_management_app.action_view_application_task').read()[0]
		action['domain'] = [('custom_application_id','in', self.ids)]
		action['context'] = {'default_application_id': self.id}
		return action

	@api.onchange('stage_id')
	def check_stage(self):
		# import pdb
		# pdb.set_trace()
		if self.is_task_created:
			if self.stage_id.name=='Draft':
				self.is_task_created = False
				self.env.cr.execute("""Update project_task set active='false' WHERE custom_application_id IN %s""", (tuple(self.ids),))

		print("Hello")

	

	# @api.multi
	def unlink(self):
		for rec in self:
			if rec.stage_id.name not in ('Draft'):
				raise UserError(_('You can not delete application now.'))
		return super(TrainingApplication, self).unlink()

class TrainingCostLine(models.Model):
	_name = "training.cost.line"
	application_cost_id = fields.Many2one(
		'emp.training.application',
		string='Application'
	)
	training_cost_id = fields.Many2one(
		'training.cost',
		string='Training'
	)
	cost = fields.Float('Cost')

class TrainingApplicationLine(models.Model):
	_name = "emp.training.application.line"
	_rec_name = 'number'
	_inherit = ['mail.thread', 'mail.activity.mixin']


	@api.model
	def _default_stage(self):
		stage_id = self.env['emp.training.application.line.stage'].search([('default_stage','=', True)],limit=1)
		return stage_id

	start_date = fields.Date(
		string='Start Date',
		required=True
	)
	end_date = fields.Date(
		string='End Date',
		required=True
	)
	app_stage_line_ids = fields.Many2one(
		'emp.training.application.line.stage', 
		string='Employee Training Stages',
		track_visibility='onchange',
		default=_default_stage,
		index=True
	)
	application_id = fields.Many2one(
		'emp.training.application', 
		string='Application'
	)
	course_id = fields.Many2one(
		'slide.channel', 
		string='Course' , 
		required=True
	)
	# subject_ids = fields.Many2many(
	# 	'training.subject',
	# 	string='Subject',
	# 	required=True
	# )
	subject_ids = fields.Many2many(
		'slide.slide',
		string='Subject',
		required=True
	)
	training_center_id = fields.Many2one(
		'emp.training.center',
		string='Training Center', 
	)
	class_room_id = fields.Many2one(
		'emp.training.class.room',
		string='Class Room',
	)
	description = fields.Text(
		string='Description'
	)
	employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
		related='application_id.employee_id',
	)
	user_id = fields.Many2one(
		'res.users',
		string='Responsible',
		default=lambda self: self.env.user,
		related='application_id.user_id',
	)
	number = fields.Char(
		string='Number',
		related='application_id.number',
	)
	project_id = fields.Many2one(
		'project.project',
		string='Project',
		related='application_id.project_id',
	)
	create_date = fields.Date(
		string='Create Date',
		default=fields.Date.context_today,
	)
	
	# @api.onchange('course_id')
	# def onchange_course_id(self):
	# 	subject_ids = [('id', 'in', self.course_id.subject_ids.ids)]
	# 	return {'domain': {'subject_ids': [('id', 'in', self.course_id.subject_ids.ids)]}}
	@api.onchange('course_id') #odoo13
	def onchange_course_id(self):
		subject_ids = [('id', 'in', self.course_id.slide_ids.ids)]
		return {'domain': {'subject_ids': [('id', 'in', self.course_id.slide_ids.ids)]}}


	# @api.multi
	# def _get_report_values(self, line):
	# 	return ', '.join([i.name for i in line.subject_ids])
	#odoo13
	def _get_report_values(self, line):
		return ', '.join([i.name for i in line.subject_ids])

	# @api.multi
	# def _get_report_doc_values(self, doc):
	# 	return ', '.join([i.name for i in doc.subject_ids])
	#odoo13
	def _get_report_doc_values(self, doc):
		return ', '.join([i.name for i in doc.subject_ids])

	# @api.multi
	def unlink(self):
		raise UserError(_('You can not delete application now.'))
		return super(TrainingApplicationLine, self).unlink()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: