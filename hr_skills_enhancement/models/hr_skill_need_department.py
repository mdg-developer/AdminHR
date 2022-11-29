# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta, date



class SkillNeedDepartment(models.Model):
    """

    class Skill(models.Model):
    name = fields.Char(required=True)
    skill_type_id = fields.Many2one('hr.skill.type')

    class EmployeeSkill(models.Model):
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    skill_id = fields.Many2one('hr.skill', required=True)
    skill_level_id = fields.Many2one('hr.skill.level', required=True)
    skill_type_id = fields.Many2one('hr.skill.type', required=True)
    level_progress = fields.Integer(related='skill_level_id.level_progress')
    """


    _name = 'hr.skill.need.department'

    skill_need_id = fields.Many2one('hr.skill.need',string='Skill needs')

    department_id = fields.Many2one('hr.department',string='Department')

    number_employee_required = fields.Integer(string='N employees required')


