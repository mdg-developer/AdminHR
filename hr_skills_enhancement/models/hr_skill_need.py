# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta, date



class SkillNeed(models.Model):
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

    _name = 'hr.skill.need'
    _order= 'skill_type_id,skill_id,skill_level_id'

    def name_get(self):
        """



        """
        result = []
        for record in self:
            name = record.skill_type_id.name + '-' + record.skill_id.name + '-'+ record.skill_level_id.name
            result.append((record.id, name))
        return result


    @api.depends('skill_id','skill_level_id','number_employee_required','skill_id.employee_ids.skill_level_id',
        'skill_id.employee_ids.skill_id','skill_id.employee_ids.target_skill_level_id')
    def _compute_number_employee(self):
        """




        """


        for record in self.env['hr.skill.need'].search([]):

            record.number_employee_ok = \
                len(record.skill_id.employee_ids.filtered(lambda r: r.skill_level_id == record.skill_level_id \
                and r.skill_id == record.skill_id))

            record.number_employee_on_progress = \
                len(record.skill_id.employee_ids.filtered(lambda r: r.target_skill_level_id == record.skill_level_id \
                                                                    and r.skill_id == record.skill_id))

            record.number_employee_all = \
                len(record.skill_id.employee_ids.filtered(lambda r: r.skill_id == record.skill_id))


            missing = record.number_employee_required- record.number_employee_ok

            record.number_employee_missing = missing if missing > 0 else 0

    #WARNING: @api.onchange('department_ids.number_employee_required) bugs
    @api.onchange('department_ids')
    def _onchange_number_employee(self):
        """

        """

        for record in self:
            global_employee_required = 0

            for department in record.department_ids:
                global_employee_required += department.number_employee_required
            record.number_employee_required = global_employee_required






    skill_type_id = fields.Many2one('hr.skill.type', required=True)

    skill_id = fields.Many2one('hr.skill',string = 'Skill',domain="[('skill_type_id','=',skill_type_id)]", required=True)
    skill_level_id = fields.Many2one('hr.skill.level',domain="[('skill_type_id','=',skill_type_id)]", required=True)

    number_employee_required = fields.Integer(string='N employees needed')
    number_employee_ok = fields.Integer(string='N employees ok',compute='_compute_number_employee',store=True)
    number_employee_on_progress = fields.Integer(string='N employees on progress',compute='_compute_number_employee',
        store=True)
    number_employee_missing = fields.Integer(string='N missing employees ',compute='_compute_number_employee',store=True)
    number_employee_all = fields.Integer(string='N all employees', compute='_compute_number_employee',
        store=True)

    date_start = fields.Date('Date start')
    date_end = fields.Date('Date end')

    color = fields.Integer(string='Color')

    active=fields.Boolean(string='Active',default=True)

    is_department_need_specified = fields.Boolean('Define needs per department ?')
    department_ids = fields.One2many('hr.skill.need.department','skill_need_id',string='Needs per department')


    def open_employee_skill(self):

        self.ensure_one()

        ctx = dict(self.env.context)
        filter_option = self.env.context.get('option')

        form_view_id  = self.env.ref('hr_skills_enhancement.employee_skill_view_form_hr_ext').id
        action={
            'name': 'rr',
            'type': 'ir.actions.act_window',
            "views": [[False, "tree"], [form_view_id, "form"]],
            'res_model': 'hr.employee.skill',
            }

        action_context={}
        action.update({'context': {'skill_id': self.skill_id.id,
                                   'skill_type_id': self.skill_type_id.id,
                                   'skill_level_id': self.skill_level_id.id}
                       })

        if filter_option == 'ok':
            action.update({'domain':[
               ('skill_id','=',self.skill_id.id),
               ('skill_level_id', '=', self.skill_level_id.id),
                ]})

        if filter_option == 'missing':

            action.update({'domain':[
               ('skill_type_id','=',None),
                ]})

        if filter_option == 'on_progress':
            action.update({'domain':[
               ('skill_id','=',self.skill_id.id),
               ('target_skill_level_id', '=', self.skill_level_id.id),
                ]})

        if filter_option == 'all':
            action.update({'domain':[
                               ('skill_id','=',self.skill_id.id)
                                ]})


        #raise UserError(str(action))
        return action







