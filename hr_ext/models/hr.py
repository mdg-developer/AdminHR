from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from openerp import models, fields
from openerp.osv import osv
import re


class HrJob(models.Model):    
    _inherit = 'hr.job'
    _description = 'Job Position'

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            name = self.search([('name', '=', self.name)])
            if name:
                raise ValidationError(_(" '%s'  already exists in Job Position !")%(self.name))

    @api.depends('job_line.total_employee')
    def compute_total_employee(self):
        for job in self:
            total_emp = 0
            for line in job.job_line:
                total_emp = total_emp + line.total_employee
            job.total_employee = total_emp
    
    # @api.depends('job_line.new_employee')
    # def compute_total_new_employee(self):
    #     for job in self:
    #         total_new_emp = 0
    #         for line in job.job_line:
    #             total_new_emp = total_new_emp + line.new_employee
    #         job.no_of_recruitment = total_new_emp

    @api.depends('total_employee', 'current_employee')
    def compute_total_new_employee(self):
        for rec in self:
            rec.no_of_recruitment = 0
            if rec.total_employee >= rec.current_employee:
                rec.no_of_recruitment = rec.total_employee - rec.current_employee
        
    @api.depends('job_line.current_employee')
    def compute_current_employee(self):
        for job in self:
            total_current_emp = 0
            
            for line in job.job_line:
                current_employee = self.env['hr.employee'].search_count([('company_id', '=',line.company_id.id),
                                                                        ('branch_id', '=', line.branch_id.id),
                                                                        ('department_id', '=', line.department_id.id),
                                                                        ('resign_date','=',False),
                                                                        ('job_id', '=', line.job_id.id)])
                total_current_emp = total_current_emp + current_employee
            job.current_employee = total_current_emp
                
    def _compute_benefit_ids(self):   
        
        benefits = self.env['hr.job.benefit'].search([('job_id', '=', self.id)])
        for job in self:
            job.benefit_count = benefits
            self.job_id='job_id'
            
            
    @api.onchange('comp_template_id')
    def onchange_comp_template_id(self):
        job = self.env['hr.job'].browse(self.user_id.id)
        if job:
                jobs = self.env['employee.performance'].create({    'employee_id':self.branch_id.manager_id.id,
                                                                    'template_id':self.template_id.id,
                                                                    'comp_template_id':self.comp_template_id.id,
                                                                })
    
    @api.constrains('job_line')
    def _constrains_job_line(self):
        if self.job_line:
            for line in self.job_line:
                new_emp = line.total_employee - line.current_employee
                if new_emp < 0:
                    raise ValidationError(_('Expected New Employee is Less Than Zero.'))
                        
    total_employee  = fields.Integer(string='Expected Total Employee',compute='compute_total_employee')
    #total_employee  = fields.Integer(string='Expected Total Employee')
    new_employee = fields.Integer(string='Expected New Employee')
    current_employee = fields.Integer(string='Current Employee',compute='compute_current_employee', store = True)
    job_grade_id = fields.Many2one('job.grade', string='Job Grade')
    skill_line = fields.One2many('skill.line', 'job_id', string='Skill')     
    job_line = fields.One2many('job.line', 'job_id', string='Job')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False,
        help='Number of new employees you expect to recruit.',compute='compute_total_new_employee')   
    appraisal_count = fields.Integer(string='Appraisals')
    benefit = fields.Char('Benefit')
    benefit_count = fields.Integer(compute='_compute_benefit_ids', string="Benefit Count")
    branch_id = fields.Many2one('res.branch', string='Branch')
    template_id = fields.Many2one('performance.template', string='Key Performance Template')
    comp_template_id = fields.Many2one('competencies.template', string='Competency Template')
    company_id = fields.Many2one('res.company', string='Company', default=False)
    jd_summary = fields.Char(string='JD Summary')

    
class SkillLine(models.Model):    
    _name = 'skill.line'    
     
    job_id = fields.Many2one('hr.job', string='Skill Line', index=True, required=True, ondelete='cascade')
    skill_id = fields.Many2one('hr.skill', required=True)
    skill_level_id = fields.Many2one('hr.skill.level', required=True)
    skill_type_id = fields.Many2one('hr.skill.type', required=True)
    level_progress = fields.Integer(related='skill_level_id.level_progress')
#     skill_type_id = fields.Many2one('hr.skill.type')
#     name = fields.Char(required=True)
#     level_progress = fields.Integer(string="Progress", help="Progress from zero knowledge (0%) to fully mastered (100%).")
#      
#     skill  = fields.Char('Skill')
#     level  = fields.Char('Level')
#     point  = fields.Float('Point')


class JobLine(models.Model):    
    _name = 'job.line'    
    _rec_name = 'job_id'
         
    @api.depends('company_id', 'branch_id', 'department_id', 'job_id')
    def _get_current_employee(self):
        for line in self:
            current_employee = 0
            if line.company_id and line.job_id:
                current_employee = self.env['hr.employee'].search_count([('company_id', '=', line.company_id.id),
                                                                        ('branch_id', '=', line.branch_id.id),
                                                                        ('department_id', '=', line.department_id.id),
                                                                        ('job_id', '=', line.job_id.id)])
            line.current_employee = current_employee
            # if line.company_id and line.job_id:
            #     employee = self.env['hr.employee'].search_count([('company_id', '=',line.company_id.id),('job_id', '=', line.job_id.id)])
            #     line.current_employee = employee
#                 if employee:
#                     line.current_employee = employee
#                 else:
#                     line.current_employee = 0
                    
    @api.depends('total_employee', 'current_employee')
    def _get_new_employee(self):
        for line in self:            
            line.new_employee = line.total_employee - line.current_employee
            line.expected_new_employee = line.new_employee
#             line.expected_new_employee = line.new_employee        
#             if line.total_employee >= line.current_employee:                
#                 line.new_employee = line.total_employee - line.current_employee
#                 line.expected_new_employee = line.new_employee
#             else:
#                 line.new_employee = 0
#                 line.expected_new_employee = line.new_employee
     
    job_id = fields.Many2one('hr.job', string='Job', index=True, required=True, ondelete='cascade')
    
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
    department_id = fields.Many2one('hr.department', string='Department')
    total_employee = fields.Integer(compute='_get_total_employee', string='Expected Total Employee')
    current_employee = fields.Integer(compute='_get_current_employee', string='Current Employee', readonly=True, store = True)
    new_employee = fields.Integer(compute='_get_new_employee', string='Expected New Employee', readonly=True)
    expected_new_employee = fields.Integer(string='New Employee')
    upper_position = fields.Many2one('hr.job', string='Upper Position')
    normal_employee = fields.Integer(string='Normal Employee')
    urgent_employee = fields.Integer(string='Urgent Employee')
    job_description = fields.Html(string='Job Description')
    job_requirment = fields.Html(string='Job Requirment')

    def get_requirment(self):
        if self.job_requirment:
            data_one = self.job_requirment
            reg = re.compile(r'<[^>]+>')
            text = reg.sub('', data_one)
        else:
            text = ''
        return text

    @api.constrains('job_requirment')
    def _check_emp_no(self):
        if self.job_requirment:
            rec = self.job_requirment
            reg = re.compile(r'<[^>]+>')
            text = reg.sub('', rec)

            if len(text) < 3000:
                raise ValidationError('Minimum must be fill 3000')

    def get_description(self):
        if self.job_description:
            data = self.job_description
            reg = re.compile(r'<[^>]+>')
            text = reg.sub('', data)
        else:
            text = ''
        return text

    @api.constrains('job_description')
    def _check_emp_no(self):
        if self.job_description:
            rec = self.job_description
            reg = re.compile(r'<[^>]+>')
            text = reg.sub('', rec)

            if len(text) > 200 or len(text) < 8000:
                raise ValidationError('Minimum must be 200 characters and Maximum 8000')






    @api.depends('normal_employee', 'urgent_employee')
    def _get_total_employee(self):
        for line in self:
            line.total_employee = line.normal_employee + line.urgent_employee


    def write(self, vals):
        old_job_id = old_manager_id = False
        employee_obj = self.env['hr.employee'].sudo()
        job_line_obj = self.env['job.line'].sudo()
        department_obj = self.env['hr.department'].sudo()
        for rec in self:
            old_job_id = rec.job_id.id
            old_upper_position_id = rec.upper_position.id
            branch_id = rec.branch_id.id
            company_id = rec.company_id.id

            job_emp_ids = employee_obj.sudo().search(
                [('company_id', '=', company_id), ('branch_id', '=', branch_id), ('job_id', '=', old_job_id)])
            result = super(JobLine, self).write(vals)
            res = self.browse([rec.id])

            if old_upper_position_id != res.upper_position.id:
                if old_job_id and branch_id and company_id:
                    for employee in job_emp_ids:
                        if res.upper_position:
                            emp_direct_mng = employee_obj.sudo().search(
                                [('company_id', '=', company_id), ('branch_id', '=', branch_id),
                                 ('job_id', '=', res.upper_position.id)],limit=1)

                        # if emp_direct_mng :
                        #     employee.write({'parent_id': emp_direct_mng,'manager_job_id': job_line.upper_position.id})
                            if emp_direct_mng:
                                employee.write(
                                    {'manager_job_id': res.upper_position.id, 'parent_id': emp_direct_mng.id})
                                # job_line = job_line_obj.sudo().search(
                                #     [('job_id', '=', res.job_id.id), ('company_id', '=', company_id),
                                #      ('branch_id', '=', branch_id), ('department_id', '=', res.department_id.id)], limit=1)
                                # if job_line and job_line.upper_position:
                                #     direct_mng = employee_obj.sudo().search(
                                #         [('company_id', '=', job_line.company_id.id),
                                #          ('branch_id', '=', job_line.branch_id.id),
                                #          ('job_id', '=', job_line.upper_position.id)], limit=1)
                                #     if direct_mng:
                                #         employee.write({'manager_job_id': job_line.upper_position.id, 'parent_id': direct_mng.id})


class HrEmploymentStatus(models.Model):
    _name = "employment.new.status"
    _description = "Employment Status"

    name = fields.Char('Employment Status')


class HrReasons(models.Model):
    _name = "hr.reasons.status"
    _description = "Hr Reasons"

    name = fields.Char('Reasons')


class Applicant(models.Model):
    _inherit = "hr.applicant"
    _description = "Applicant"

    date_of_birth = fields.Date('Date Of Birth')
    nrc = fields.Char('NRC')
    qualification = fields.Char('Qualification')
    applied_date = fields.Date('Applied Date')
    noticed_period = fields.Char('Noticed Period')
    send_offer = fields.Char('Send Offer')
    offer_date = fields.Date('Offer Date')
    current_company = fields.Char('Current Company')
    current_position = fields.Char('Current Position')
    current_salary = fields.Integer('Current Salary')
    final_interview = fields.Date('Final Interview Date')
    date_of_send = fields.Date('Date Of Send To HOD')
    hr_received_date = fields.Date('Hr Received Date')
    employment_status = fields.Many2one('employment.new.status')
    cv_attached = fields.Char('CV Attached')
    hod_name = fields.Char('HOD Name')
    withdraw = fields.Char('withdraw')


    @api.model
    def _default_nrc_type(self):
        return self.env['res.nrc.type'].search([('name', '=', 'N')]).id

    @api.model
    def _default_nrc_region_code(self):
        return self.env['res.nrc.region'].search([('name', '=', '12')]).id

    @api.onchange('nrc_region_code')
    def _onchange_nrc_region_code(self):
        if self.nrc_region_code and self.nrc_prefix:
            if self.nrc_region_code != self.nrc_prefix.nrc_region:
                self.nrc_prefix = False

    @api.onchange('nrc_region_code', 'nrc_region_code', 'nrc_type', 'nrc_number')
    def _onchange_nrc_number(self):
        if self.nrc_region_code and self.nrc_prefix and self.nrc_type and self.nrc_number:
            self.nrc = self.nrc_region_code.name + '/' + self.nrc_prefix.name + '(' + self.nrc_type.name + ')' + str(self.nrc_number)

    nrc_region_code = fields.Many2one("res.nrc.region", string='Region', default=_default_nrc_region_code)
    nrc_prefix = fields.Many2one("res.nrc.prefix", string='Prefix')
    nrc_type = fields.Many2one("res.nrc.type", string='Type', default= _default_nrc_type)
    nrc_number = fields.Char('NRC Entry', size=6)
    requisition_date = fields.Date(string="Requisition Date")
    job_announcement_date = fields.Date(string="Job Announcement Date")


    branch_id = fields.Many2one('res.branch', string='Branch')
    replace_for = fields.Boolean(string='Replace For?', default=False)
    reason_for = fields.Many2one('hr.reasons.status')

    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            job_line = self.env['job.line'].sudo().search([('job_id', '=', applicant.job_id.id),
                                                            ('company_id', '=', applicant.company_id.id),
                                                            ('branch_id', '=', applicant.branch_id.id),
                                                            ('department_id', '=', applicant.department_id.id)], limit=1)
            same_position_resign_employee = self.env['hr.employee'].sudo().search([('job_id', '=', applicant.job_id.id),
                                                                                    ('company_id', '=', applicant.company_id.id),
                                                                                    ('branch_id', '=', applicant.branch_id.id),
                                                                                    ('department_id', '=', applicant.department_id.id),
                                                                                    ('resign_date', '!=', False)])
            if job_line and job_line.total_employee <= job_line.current_employee and not same_position_resign_employee:
                raise ValidationError(_('Cannot Create New Employee for %s Position. Expected New Employee Zero.') % (applicant.job_id.name))
#             contact_name = False
#             if applicant.partner_id:
#                 address_id = applicant.partner_id.address_get(['contact'])['contact']
#                 contact_name = applicant.partner_id.display_name
#             else:
#                 if not applicant.partner_name:
#                     raise UserError(_('You must define a Contact Name for this applicant.'))
#                 new_partner_id = self.env['res.partner'].create({
#                     'is_company': False,
#                     'type': 'private',
#                     'name': applicant.partner_name,
#                     'email': applicant.email_from,
#                     'phone': applicant.partner_phone,
#                     'mobile': applicant.partner_mobile
#                 })
#                 address_id = new_partner_id.address_get(['contact'])['contact']
#             if applicant.partner_name or contact_name:
            if applicant.partner_name:
                employee = self.env['hr.employee'].create({
                    'name': applicant.partner_name,
                    'company_id': applicant.company_id.id or False,
                    'branch_id': applicant.branch_id.id or False,
                    'job_id': applicant.job_id.id or False,
                    'job_title': applicant.job_id.name,
                    'nrc_region_code': applicant.nrc_region_code.id,
                    'nrc_prefix': applicant.nrc_prefix.id,
                    'nrc_type': applicant.nrc_type.id,
                    'nrc_number': applicant.nrc_number,
                    'nrc': applicant.nrc,
                    'qualification': applicant.qualification,
                    # 'address_home_id': address_id,
                    'department_id': applicant.department_id.id or False,
                    'address_id': applicant.company_id and applicant.company_id.partner_id
                            and applicant.company_id.partner_id.id or False,
                    'work_email': applicant.department_id and applicant.department_id.company_id
                            and applicant.department_id.company_id.email or False,
                    'work_phone': applicant.department_id and applicant.department_id.company_id
                            and applicant.department_id.company_id.phone or False})
                applicant.write({'emp_id': employee.id})
                if applicant.job_id:
                    applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                    applicant.job_id.message_post(
                        body=_('New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                        subtype="hr_recruitment.mt_job_applicant_hired")
                applicant.message_post_with_view(
                    'hr_recruitment.applicant_hired_template',
                    values={'applicant': applicant},
                    subtype_id=self.env.ref("hr_recruitment.mt_applicant_hired").id)

            # If manager position is hired, to update manager in employee
            if employee:
                emp_with_same_manager_objs = self.env['hr.employee'].sudo().search([('manager_job_id', '=', employee.job_id.id),
                                                                                    ('company_id', '=', employee.company_id.id),
                                                                                    ('branch_id', '=', employee.branch_id.id),
                                                                                    ('department_id', '=', employee.department_id.id)])
                if emp_with_same_manager_objs:
                    for mgr in emp_with_same_manager_objs:
                        mgr.write({
                            'parent_id': employee.id
                        })

        employee_action = self.env.ref('hr.open_view_employee_list')
        dict_act_window = employee_action.read([])[0]
        dict_act_window['context'] = {'form_view_initial_mode': 'edit'}
        dict_act_window['res_id'] = employee.id
        return dict_act_window

