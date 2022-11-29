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
import logging

_logger = logging.getLogger(__name__)

class EmployeeSkill(models.Model):
    _inherit = 'hr.employee.skill'

    _order = 'skill_type_id,skill_id,skill_level_id'




    def _default_employee_id(self):
        """


        _getCreateLineContext: function (group) {
        var ctx = this._super(group);
        return group ? _.extend({ default_skill_type_id0: group[0].data[this.groupBy].data.id }, ctx) : ctx;
        },

        """
        return self.env.context.get('employee_id')

    @api.onchange('skill_id')
    def _skill_type_id(self):
        """

        """

        for record in self:
            record.skill_level_id = None
            for line in record.employee_skill_followup_ids:
                record.update({'employee_skill_followup_ids':
                    [(1,line.id, {
                        'initial_skill_level_id': None,
                        'target_skill_level_id': None,
                        'skill_id': record.skill_id.id,
                    })]})

            return



    @api.onchange('skill_type_id')
    def _skill_type_id(self):
        """

        order_lines = []
        for line in test_lines:
            order_lines.append((0, 0, {
                'name': name,
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
            }))
        self.order_line = order_lines
        :return:
        """

        for record in self:
            # WARNING Updating context requires to return action def with updated context
            # when form opened from kanban <Skill need>, pbm

            if record.env.context.get('skill_id') and not record.is_new:
                _logger.debug('------------------------------------------------------------------------1')
                record.is_new = True
            else:
                _logger.debug('-------------------------------------------------------------------------2')
                record.skill_id = None
                record.skill_level_id = None

            for line in record.employee_skill_followup_ids:
                record.update({'employee_skill_followup_ids':
                    [(1,line.id, {
                        'skill_type_id': record.skill_type_id.id,
                        'skill_id': record.skill_id.id,
                        'target_skill_level_id': None
                    })]})

            return

    @api.depends('skill_level_id','employee_skill_followup_ids') # WARNING No '.' towards 'many' field : bug with NewId
    def _compute_target_skill_xxxx(self):
        """


        """


        for record in self:
            record.state = 'no_action'
            record.target_skill_level_id = None #
            record.target_skill_assessment_deadline = None #
            record.target_skill_date_assessment = None  #
            record.target_skill_assessment_result = None

            for followup_line in record.employee_skill_followup_ids:
                if not isinstance(followup_line.id, models.NewId):
                    record.target_skill_assessment_user_id = followup_line.assessment_user_id.id
                    if not followup_line.assessment_result:
                        record.state = 'on_progress'
                        record.target_skill_level_id = followup_line.target_skill_level_id.id
                        record.target_skill_assessment_deadline = followup_line.assessment_deadline
                    elif followup_line.assessment_result == 'pass':
                        record.state = 'pass'
                        record.skill_level_id = followup_line.target_skill_level_id.id
                        record.target_skill_date_assessment = followup_line.date_assessment
                        record.target_skill_assessment_result = followup_line.assessment_result
                    elif followup_line.assessment_result == 'fail':
                        record.state = 'fail'
                        record.target_skill_date_assessment = followup_line.date_assessment
                        record.target_skill_assessment_result = followup_line.assessment_result
                    break
    # lambda self: self.env.context.get('employee_id')
    employee_id = fields.Many2one('hr.employee', required=True,
        default=_default_employee_id ,
        ondelete='cascade')


    skill_type_id = fields.Many2one('hr.skill.type',
                                    default= lambda self: self.env.context.get('skill_type_id'),
                                    string='Skill type')


    skill_id = fields.Many2one('hr.skill', domain="[('skill_type_id','=',skill_type_id)]",
                               default=lambda self: self.env.context.get('skill_id'),
                               string='Skill')



    target_skill_level_id = fields.Many2one('hr.skill.level', compute= '_compute_target_skill_xxxx',
        store=True,string="Target skill level")

    target_skill_assessment_deadline = fields.Date(compute= '_compute_target_skill_xxxx',
        store=True,string="Assessment deadline")

    target_skill_assessment_user_id = fields.Many2one('res.users',compute= '_compute_target_skill_xxxx',
        store=True,string='Assessor')

    target_skill_date_assessment = fields.Date(compute='_compute_target_skill_xxxx',
                                        store=True, string="Assessment date")

    target_skill_assessment_result = fields.Selection([('pass','Pass'),('fail','Fail')],
        compute='_compute_target_skill_xxxx',
        store=True, string="Assessment result") # WARNING selection list compulsory in computed field

    employee_skill_followup_ids = fields.One2many('hr.employee.skill.followup', 'employee_skill_id', string='Employee')

    date_start = fields.Date('Start date')
    date_end = fields.Date('End date')
    state = fields.Selection([('no_action','No action'),('on_progress', 'On progress'),('pass', 'Passed'), ('fail', 'Failed')],
                                                      compute='_compute_target_skill_xxxx',
                                                      store=True,
                                                      string="state")  # WARNING selection list compulsory in computed field

    color = fields.Integer(string='Color')

    is_new  = fields.Boolean(string='Test')





