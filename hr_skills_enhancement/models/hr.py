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


#import uuid

#from itertools import groupby
from datetime import datetime, timedelta, date
#from werkzeug.urls import url_encode

from odoo import api, fields, models, _
#from odoo.exceptions import UserError, AccessError
#from odoo.osv import expression
#from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
#from odoo.tools.misc import formatLang

from odoo.addons import decimal_precision as dp

#from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


"""





    hr_category
    hr_domain
    hr_grade
    hr_salary_scale


    hr_employee(inherited)
    hr_career


    hr_skill
    hr_skill_employee_rel


    hr_training
    hr_training_request
    hr_training_employee_rel

    hr_qualification
    hr_qualification_employee_rel

    hr_education_background
    hr_education_item


"""


# CONFIGURATION



def create_career(self, current_year):
    """
    warning: must be called
    """

    employee_id = self.id
    date_start = str(current_year)+'-01-01 00:00:00'
    date_end = str(current_year)+'-12-31 23:59:00'


    #raise Warning(date_start)

    """
    
    SELECT
    hr_position.employee_id,hr_position.contract_type_id,
    hr_position.analytic_account_id, hr_position.quotity,
    hr_promotion.grade_id,hr_promotion.level,hr_promotion.code_pab,hr_promotion.salary_scale_id,
    hr_position.date_start as position_date_start,
    hr_position.date_end as position_date_end,
    hr_promotion.date_start as promotion_date_start,
    hr_promotion.date_end as promotion_date_end,
    case  when hr_promotion.date_start > hr_position.date_start then hr_promotion.date_start 
        else hr_position.date_start end 
        as date_start,
    case  when hr_promotion.date_end < hr_position.date_end then hr_promotion.date_end 
        else hr_position.date_end end 
        as date_end

    FROM hr_promotion, hr_position
    WHERE
    hr_position.employee_id = %s and
    hr_promotion.employee_id = hr_position.employee_id and
    (
    (hr_promotion.date_end >= hr_position.date_start and
    hr_promotion.date_end <= hr_position.date_end )
    or
    (hr_promotion.date_start >= hr_position.date_start and
    hr_promotion.date_start <= hr_position.date_end)
    )
    order by hr_position.date_start;
    """

    sql = '''
    SELECT
    hr_position.employee_id, hr_position.contract_type_id,
    hr_position.analytic_account_id, hr_position.quotity,
    hr_promotion.grade_id, hr_promotion.level,hr_promotion.code_pab, hr_promotion.salary_scale_id,
    hr_position.date_start as position_date_start,
    hr_position.date_end as position_date_end,
    hr_promotion.date_start as promotion_date_start,
    hr_promotion.date_end as promotion_date_end,
    case
        when hr_promotion.date_start > hr_position.date_start
            then hr_promotion.date_start else hr_position.date_start end as date_start,
    case 
        when hr_promotion.date_end is Null and hr_position.date_end is Null
            then %s     
        when hr_position.date_end is null
            then hr_promotion.date_end
              
        else hr_position.date_end end as date_end
    
    FROM
    hr_promotion, hr_position
    WHERE
    hr_position.employee_id = %s and
    hr_promotion.employee_id = hr_position.employee_id and
    
    (
    (hr_promotion.date_end >= %s OR hr_promotion.date_end IS NULL) AND
    hr_promotion.date_start <= %s AND
    (hr_position.date_end >= %s OR hr_position.date_end IS NULL) AND 
    hr_position.date_start <= %s
    )
    
    and
    (
            ((hr_promotion.date_end >= hr_position.date_start or hr_promotion.date_end IS NULL) and
             (hr_promotion.date_end <= hr_position.date_end or hr_position.date_end IS NULL))
            or
            (hr_promotion.date_start >= hr_position.date_start and
             (hr_promotion.date_start <= hr_position.date_end or hr_promotion.date_end IS NULL)
             )
    )
    
    order by hr_position.date_start, hr_promotion.date_start;'''



    self.env.cr.execute(sql, (date_end,employee_id,date_start,date_end,date_start,date_end))
    lines = self.env.cr.dictfetchall() # warning self redefining like below empties it

    first_day = datetime(current_year, 1, 1,0,0,0)
    last_day = datetime(current_year, 12, 31,0,0,0)
    n_day_per_year = (last_day - first_day).days + 1

    for line in lines:

        date_start = fields.datetime.strptime(line['date_start'], '%Y-%m-%d')

        if line['date_end']:
            date_end = fields.datetime.strptime(line['date_end'], '%Y-%m-%d')
        else:
            date_end= last_day

        if date_start < first_day:
            date_start = first_day

        if date_end > last_day:
            date_end = last_day

        annual_cost = 0
        n_day = 0

        n_day = (date_end - date_start).days + 1
        quotity = line['quotity']
        fulltime_rate =  (n_day* quotity)/n_day_per_year


        salary_scale_lines = self.env['hr.salary.scale.line'].search(
            [('salary_scale_id', '=', line['salary_scale_id'] ),
             ('grade_id', '=', line['grade_id'] ),
             ('level', '=', line['level']  )], order='id desc')


        for salary_scale_line in salary_scale_lines:
            annual_cost = salary_scale_line.annual_cost

        career = self.env['hr.career'].search([('employee_id', '=',employee_id)])
        career.create({'employee_id': employee_id,'contract_type': line['contract_type_id'],
            'date_start': date_start,'date_end': date_end, 'quotity': line['quotity'],
            'analytic_account_id': line['analytic_account_id'],
            'grade_id': line['grade_id'], 'level': line['level'],'code_pab':line['code_pab'],
            'salary_scale_id': line['salary_scale_id'],
            'contract_type_id': line['contract_type_id'],
            'annual_cost': annual_cost,
            'start_end_year': date_start.strftime('%Y'),
            'fulltime_rate': fulltime_rate,
            'period_cost': annual_cost * fulltime_rate
        })





class hr_contract_type(models.Model):
    """

    """

    _name = "hr.contract.type"
    _description = 'Contract types'

    name = fields.Char('Name', size=150, required=True)
    default_salary_scale_id = fields.Many2one('hr.salary.scale', string='Default salary scale', index=True)

    """
    class hr_domain(models.Model):
        
    
     
    
        _name = "hr.domain"
        _description = 'Domain'
    
        nature = fields.Selection([('qual', 'Qualification'),
            ('train', 'Training'), ('score', 'Score'),('skill_assessment','Skill assessment')], 'Nature',
            select=True)
        name = fields.Char('Name', size=150, required=True)
    
    """


class hr_grade(models.Model):
    """

    """

    _name = "hr.grade"
    _description = 'Grade'

    name = fields.Char('Name', size=128, required=True)
    description = fields.Text('Description')
    partner_id = fields.Many2one('res.partner', 'Partner', index=True)
    career_ids = fields.One2many('hr.career', 'grade_id', string='Careers')


class hr_salary_scale(models.Model):
    """

    """

    _name = "hr.salary.scale"
    _description = 'Salary scales'

    name = fields.Char('Name', required=True)
    description = fields.Text(string='Description')

    salary_scale_line_ids = fields.One2many('hr.salary.scale.line','salary_scale_id',string='Lines')



class hr_salary_scale_line(models.Model):
    """

    """

    _name = "hr.salary.scale.line"
    _description = 'Salary scale line'

    """
    update hr_salary_scale_line set grade_id = hr_grade.id
    from hr_grade
    where hr_salary_scale_line.description = hr_grade.description;
    """



    date_start = fields.Date(string = 'Date start')
    date_end = fields.Date(string = 'Date end')
    grade_id = fields.Many2one('hr.grade',string= 'Grade', index=True)
    level = fields.Char(string = "Level", size=10)
    information = fields.Text(string='Information')
    salary_scale_id = fields.Many2one('hr.salary.scale', string='Salary scale', index=True)
    annual_cost = fields.Float(string='Annual Cost')
    hourly_cost = fields.Float('Hourly Cost')
    area_external_id = fields.Char(size=10,string='Area')
    active = fields.Boolean('Active',
                            help="If the active field is set to False, it will allow you to hide the project without removing it.",
                            default=True)
    description = fields.Text(string='Description')



class hr_promotion(models.Model):
    """

    """

    _name = "hr.promotion"
    _description = 'Promotions'

    @api.model
    def create(self, values):
        """

        """

        new_record = super(hr_promotion, self).create(values)

        #update_career(self, new_record.employee_id.id, fields.datetime.today().year)

        return new_record  # tokn si pas id, le bouton reste affiché


    def write(self, values):
        """

        """

        for record in self:
            current_record = super(hr_promotion, record).write(values)

            #update_career(self, record.employee_id.id, fields.datetime.today().year)

        return current_record


    @api.depends('date_end')
    def compute_year_end(self):
        for record in self:
            if record.date_end:
                record.year_end = fields.datetime.strptime(record.date_end, '%Y-%m-%d').year

    @api.model
    def _default_salary_scale_id(self):
        if self.employee_id.position_ids:
            for position in self.employee_id.position_ids:
                return position.contract_type_id.default_salary_scale_id.id
        return






    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    salary_scale_id = fields.Many2one('hr.salary.scale',default=_default_salary_scale_id, string='Salary scale', index=True)
    grade_id = fields.Many2one('hr.grade', 'Grade', index=True)
    level = fields.Char('Level', size=5)

    code_pab = fields.Selection([('A', 'A'), ('B', 'B'),('C', 'C'),('D', 'D'),('E', 'E'),('F', 'F'),('G', 'G'),('H', 'H'),('J', 'J'),('G', 'G')], string='PAB', select=True)

    date_start = fields.Date('Date start', required=True)
    date_end = fields.Date('Date end')

    year_end = fields.Integer('Year end',compute='compute_year_end',store=True)

    active = fields.Boolean(string='Active', default=True)


class hr_position(models.Model):
    """

    positions must correspond to 1 full year


    """

    _name = "hr.position"
    _description = 'Positions'

    @api.model
    def create(self, values):
        """

        """

        new_record = super(hr_position, self).create(values)

        #update_career(new_record, new_record.employee_id.id, fields.datetime.today().year)

        return new_record  # tokn si pas id, le bouton reste affiché


    def write(self, values):
        """

        """
        for record in self:

            current_record = super(hr_position, record).write(values)

            #update_career(record, current_record.employee_id.id, fields.datetime.today().year)

        return current_record


    @api.depends('quotity', 'date_start', 'date_end', 'analytic_account_id')
    def _update_data(self):
        """

        Update cost (current year)period_cost

        """

        for record in self:
            #hr_career.update_career(fields.datetime.today().year, record)
            a=0


    @api.depends('date_end')
    def compute_year_end(self):
        for record in self:
            if record.date_end:
                record.year_end = fields.datetime.strptime(record.date_end, '%Y-%m-%d').year




    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    contract_type_id = fields.Many2one('hr.contract.type', string='Contract type')
    date_start = fields.Date('Date start', required=True)
    date_end = fields.Date('Date end')
    department_id = fields.Many2one('hr.department', 'Department', index=True)
    quotity = fields.Float('Quotity')
    analytic_account_id = fields.Many2one('account.analytic.account',onupdate='cascade', string='Analytic Account')

    information = fields.Text('Information')
    year_end = fields.Integer(string='Year end', compute='compute_year_end', store=True)

    active = fields.Boolean(string='Active', default=True)
    mission_ids = fields.One2many('hr.mission.position.rel', 'position_id', string='Positions')

class hr_career(models.Model):
    """

    select * from hr_position where

      date_start >=  pr.date_start and pr.date_end is null
      or
      date_start >=  pr.date_start and pr.date_end >=




    """

    _name = "hr.career"
    _description = 'Career'


    def name_get(self):
        result = []
        for record in self:
            #name = '[' + str(record.id) + ']' + ' ' + record.employee_id.name
            name =  record.employee_id.name + ' - ' + (record.grade_id.name if record.grade_id else '')  + ' - ' + (record.analytic_account_id.name if record.analytic_account_id else '')
            result.append((record.id, name))

        return result


    @api.depends('date_start', 'date_end')
    def _update_grade_id_level(self):
        """

        """






        return

        for record in self:

            # record.grade_id= 5
            if not isinstance(record.id, models.NewId):
                record.level = 5

                self.env.cr.execute('''
                    select prom.grade_id, prom.level
                    from hr_promotion prom
                    where prom.employee_id = %s
                    and prom.date_start <= %s
                    and
                    ( prom.date_end is null or prom.date_end >= %s);''',
                                    (record.employee_id.id, record.date_start, record.date_end))

        return

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_type_id = fields.Many2one('hr.contract.type', string='Contract type')
    date_start = fields.Date('Date start', required=True)
    date_end = fields.Date('Date end')
    department_id = fields.Many2one('hr.department', 'Department', index=True)
    quotity = fields.Float(string='Quotity')

    analytic_account_id = fields.Many2one('account.analytic.account',onupdate='cascade',string= 'Analytic Account')
    salary_scale_id = fields.Many2one('hr.salary.scale', string='Salary scale category', index=True)
    grade_id = fields.Many2one('hr.grade', string='Grade', index=True)
    level = fields.Char(string='Level', size=10)
    code_pab = fields.Selection(
        [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F'), ('G', 'G'), ('H', 'H'),('J', 'J')],
        'PAB',select=True)


    information = fields.Text('Information')
    annual_cost = fields.Float(string='Annual Cost')
    period_cost = fields.Float(string='Period cost')
    fulltime_rate = fields.Float(string='Fulltime rate')
    start_end_year = fields.Integer(string='Year')


"""
class hr_mission_employee_rel(models.Model):
    
   
    _name = "hr.mission.employee.rel"
    _description = 'Mission employee rel'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    mission_id = fields.Many2one('hr.mission', string='Mission')
    quotity = fields.Integer('Score')
    date_start = fields.Date('Date start')
    date_end = fields.Date('Date end')

 """


class hr_mission_position_rel(models.Model):
    """


    """

    _name = "hr.mission.position.rel"
    _description = 'Mission position rel'

    position_id = fields.Many2one('hr.position', string='Position')
    mission_id = fields.Many2one('hr.mission', string='Mission')
    quotity = fields.Integer('Quotity')
    date_start = fields.Date('Date start')
    date_end = fields.Date('Date end')




class hr_education_background(models.Model):
    _name = "hr.education.background"
    _description = 'Education background'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char('Name', required=True)
    obtaining_date = fields.Date('Obtaining date')
    information = fields.Text('Informations')
    speciality_id = fields.Many2one('hr.education.item', 'Speciality', index=True, domain=[('nature', '=', 'spe')])
    education_level_id = fields.Many2one('hr.education.item', 'Education level', index=True,
                                         domain=[('nature', '=', 'Level')])
    diploma_id = fields.Many2one('hr.education.item', 'Diploma', index=True, domain=[('nature', '=', 'dipl')])


class hr_education_item(models.Model):
    _name = "hr.education.item"
    _description = 'Education_item'

    nature = fields.Selection([('spe', 'Speciality'), ('level', 'Education level'), ('dipl', 'diploma')], 'Nature',
                              select=True)
    name = fields.Char('Name')
