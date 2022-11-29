# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class TrainingApplicationStage(models.Model):
	_name = "emp.training.application.stage"

	name = fields.Char(
		string='Name',
		required=True
	)
	is_approve = fields.Boolean(
		string='Is Approved?'
	)
	is_cancel = fields.Boolean(
		string='Is Cancelled?'
	)
	is_draft = fields.Boolean(
		string='Is Draft?'
	)
	default_stage = fields.Boolean(
		string='Default Stage'
	)

class TrainingApplicationLineStage(models.Model):
	_name = "emp.training.application.line.stage"

	name = fields.Char(
		string='Name', 
		required=True
	)
	is_draft = fields.Boolean(
		string='Is Draft?'
	)
	default_stage = fields.Boolean(
		string='Default Stage'
	)
	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: