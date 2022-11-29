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






class hr_skill_employee_followup(models.Model):  # <> employee
    """

    default=lambda self: self.env.context.get('employee_skill_id'),

    related='employee_skill_id.skill_type_id'

    @api.onchange('employee_skill_id.skill_type_id')
    def skill_type_id(self):
        raise UserError ('')
        for record in self:
            record.skill_type_id = record.employee_skill_id.skill_type_id.id

    default= lambda self: self.env.context.get('employee_skill_id'))
    employee_skill_id.skill_type_id


    @api.depends('employee_skill_id.skill_type_id')
    def _compute_skill_type_id(self):
        for record in self:
            #raise UserError(record.employee_skill_id.skill_type_id.id)
            record.skill_type_id = record.employee_skill_id.skill_type_id.id

    """

    _name = 'hr.employee.skill.followup'
    _order = 'skill_type_id,skill_id,target_skill_level_id'

    def name_get(self):
        result = []
        for record in self:
            name = record.employee_id.name + '-' + record.skill_id.name + '-'+ record.target_skill_level_id.name
            result.append((record.id, name))
        return result


    employee_skill_id = fields.Many2one('hr.employee.skill', string='Employee skill')
    skill_id = fields.Many2one('hr.skill',string='Skill', related='employee_skill_id.skill_id',store=True)
    employee_id = fields.Many2one('hr.employee', related='employee_skill_id.employee_id' ,
        string='Employee',store=True)

    # warning immediate update needed (compute or related update after saving)
    # for target_skill_level_id domain

    skill_type_id = fields.Many2one('hr.skill.type',
                                    default= lambda self: self.env.context.get('skill_type_id'))

    # warning immediate update needed (compute or related update after saving)
    initial_skill_level_id = fields.Many2one('hr.skill.level',
        default=lambda self: self.env.context.get('skill_id'),
        store=True, string='Initial level')

    target_skill_level_id = fields.Many2one('hr.skill.level',required=True,
        domain="[('skill_type_id','=',skill_type_id)]",string='Target level')

    assessment_deadline = fields.Date(string='Assessment deadline',required=True)

    date_assessment = fields.Date(string='Assessment date')
    assessment_user_id = fields.Many2one('res.users',
        string='Assessor', default = lambda r: r.write_uid.id)

    assessment_result  = fields.Selection([('pass','Pass'),('fail','Fail')],string="Assessment result")
    comment = fields.Text(string='Comment')

    active=fields.Boolean(string='Active',default=True)

    #@api.constraints()
