# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta, date


class Skill(models.Model):
    """

    class Skill(models.Model):
        _name = 'hr.skill'
        _description = "Skill"

        name = fields.Char(required=True)
        skill_type_id = fields.Many2one('hr.skill.type')


    class EmployeeSkill(models.Model):
        _name = 'hr.employee.skill'
        _description = "Skill level for an employee"
        _rec_name = 'skill_id'
        _order = "skill_level_id"

        employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
        skill_id = fields.Many2one('hr.skill', required=True)
        skill_level_id = fields.Many2one('hr.skill.level', required=True)
        skill_type_id = fields.Many2one('hr.skill.type', required=True)
        level_progress = fields.Integer(related='skill_level_id.level_progress')

        _sql_constraints = [
            ('_unique_skill', 'unique (employee_id, skill_id)', "Two levels for the same skill is not allowed"),
        ]

        @api.constrains('skill_id', 'skill_type_id')
        def _check_skill_type(self):
            for record in self:
                if record.skill_id not in record.skill_type_id.skill_ids:
                    raise ValidationError(_("The skill %s and skill type %s doesn't match") % (record.skill_id.name, record.skill_type_id.name))

        @api.constrains('skill_type_id', 'skill_level_id')
        def _check_skill_level(self):
            for record in self:
                if record.skill_level_id not in record.skill_type_id.skill_level_ids:
                    raise ValidationError(_("The skill level %s is not valid for skill type: %s ") % (record.skill_level_id.name, record.skill_type_id.name))


    class SkillLevel(models.Model):
        _name = 'hr.skill.level'
        _description = "Skill Level"
        _order = "level_progress desc"

        skill_type_id = fields.Many2one('hr.skill.type')
        name = fields.Char(required=True)
        level_progress = fields.Integer(string="Progress", help="Progress from zero knowledge (0%) to fully mastered (100%).")


    class SkillType(models.Model):
        _name = 'hr.skill.type'
        _description = "Skill Type"

        name = fields.Char(required=True)
        skill_ids = fields.One2many('hr.skill', 'skill_type_id', string="Skills", ondelete='cascade')
        skill_level_ids = fields.One2many('hr.skill.level', 'skill_type_id', string="Levels", ondelete='cascade')

    """
    _inherit = "hr.skill"
    _order = "skill_type_id,name"
    #_name = "hr.skill"
    #_description = 'Skill'

    #name = fields.Char('Name', size=200)
    #description = fields.Text('Description')

    #tag_ids = fields.Many2many('hr.employee.category', string='Tags', domain=[('nature', '=', 'typ')])
    #target_score = fields.Integer('Target score')
    sequence = fields.Integer(string='Order')
    employee_ids = fields.One2many('hr.employee.skill', 'skill_id', string='Employee')


