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



class Employee(models.Model):
    """


    def create_xxxx(self):

        date_start = '2017-01-01 00:00:00'
        date_end =   '2017-12-31 00:00:00'

        position = self.env['hr.position'].search([('id', '!=', 0)])
        promotion = self.env['hr.promotion'].search([('id', '!=', 0)])
        #for position in  self.env['hr.position'].search([('id', '!=', 0)]): warnings works too


        for employee in self.env['hr.employee'].search([('id','!=',0),('active','=',True)]):
            position.create({'employee_id': employee.id,'contract_type_id':1,
                    'date_start': date_start,'date_end': date_end,'quotity':1})

            promotion.create({'employee_id': employee.id,'salary_scale_id':1,
                'date_start': date_start,'date_end': date_end})


    def update_career(self):

        ## warning : self.env['hr.career'].search([('employee_id', '!=', 0)]) dnw
        career = self.env['hr.career'].search([('id', '!=', 0)])

        career.unlink()



        for employee in self.env['hr.employee'].search([('id', '!=', 0)]):

            create_career(employee, 2017)
            create_career(employee, 2018)

    @api.model
    def create(self, values):


        new_record = super(hr_employee, self).create(values)

        #create_career(self, new_record.id, fields.datetime.today().year)


        return new_record  # tokn si pas id, le bouton reste affiché



    def write(self, values):

        for record in self:
            current_record = super(hr_employee, record).write(values)

            #create_career(self, record.id, fields.datetime.today().year)

        return current_record










    blood_group = fields.Selection(
        [('0', 'A+'), ('1', 'A-'), ('2', 'B+'), ('3', 'B-'), ('4', 'O+'), ('5', 'O-'), ('6', 'AB+'), ('7', 'AB-')],
        'Blood group', select=True)
    medical_information = fields.Text('Medical informations')
    contact = fields.Text('Contact')
    category_id = fields.Many2one('hr.employee.category', 'Category', index=True,
                                               domain=[('nature', '=', 'job')])
    maiden_name = fields.Char('Maiden name', size=75)
    work_registration_number = fields.Integer('Work registration No')

    contract_type_id = fields.Many2one('hr.contract.type', string='Contract type')
    career_ids = fields.One2many('hr.career', 'employee_id', string='Careers')
    promotion_ids = fields.One2many('hr.promotion', 'employee_id', string='Promotions',copy=True)
    position_ids = fields.One2many('hr.position', 'employee_id', string='Positions',copy=True)

    # qualification_employee_ids = fields.One2many ('hr.qualification.employee.rel','employee_id', string='Qualification employee') del20160113
    training_ids = fields.One2many('hr.training.employee.rel', 'employee_id', string='Training')
    qualification_ids = fields.One2many('hr.qualification.employee.rel', 'employee_id', string='Qualification')
    #skill_ids = fields.One2many('hr.skill.employee.rel', 'employee_id', string='Skill employee')
    education_background_ids = fields.One2many('hr.education.background', 'employee_id', string='Education background')
    # training_ids = fields.Many2many('hr.training','hr_training_employee_rel','employee_id','training_id')
    # qualification_ids = fields.Many2many('hr.qualification','hr_qualification_employee_rel','employee_id','qualification_id')


    partner_phone = fields.Char(related='address_home_id.phone', store=False)
    partner_mobile = fields.Char(related='address_home_id.mobile', store=False)

    code_pab = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'),('D', 'D'),('E', 'E'),('F', 'F'),('G', 'G'),('H', 'H'),('J', 'J')], 'PAB', select=True)

    on_progress_employee_skill_ids = fields.One2many('')



    """

    _inherit = 'hr.employee'


    on_progress_employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id',
        domain=[('state','=','on_progress')], string="Skills")