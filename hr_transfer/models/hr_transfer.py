from odoo import api, fields, models, _
from datetime import timedelta


class EmployeeTransfer(models.Model):    
    _name = 'hr.transfer'
    _description = 'Transfers'
    
    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], order='id desc', limit=1).id
    
    name = fields.Char(string='Name', copy=False, default="/", readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date(string='Date', default=fields.Date.today(), help="Date")
    state = fields.Selection([('draft', 'New'),
                              ('request', ' Requested'),
                              ('transfer', 'Transferred'),
                              ('cancel', 'Cancelled'),
                              ('done', 'Done')
                              ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    note = fields.Text(string='Internal Notes')
    transfer_no = fields.Char(string='Transfer NO')
    responsible = fields.Many2one('hr.employee', string='Responsible', default=_default_employee, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch')
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Job Position')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    new_company_id = fields.Many2one('res.company', string='New Company', copy=False, required=True, default=lambda self: self.env.company)
    new_branch_id = fields.Many2one('res.branch', string='New Branch')
    new_department_id = fields.Many2one('hr.department', 'New Department')
    new_job_id = fields.Many2one('hr.job', 'New Job Position')
    new_job_grade_id = fields.Many2one('job.grade', string='New Job Grade')
    new_salary_level_id = fields.Many2one('salary.level', string='New Salary Level')
    new_wage = fields.Float('New Wage')
    requested_employee_id = fields.Many2one('hr.employee', string='Requested Person')
    approved_employee_id = fields.Many2one('hr.employee', string='Approved Person')

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            employee = self.employee_id
            self.branch_id = employee.branch_id.id
            self.department_id = employee.department_id.id
            self.job_id = employee.job_id.id
            self.company_id = employee.company_id.id
            self.new_branch_id = employee.branch_id.id
            self.new_department_id = employee.department_id.id
            self.new_job_id = employee.job_id.id
            self.new_company_id = employee.company_id.id
            if employee.contract_id:
                self.new_job_grade_id = employee.contract_id.job_grade_id.id
                self.new_salary_level_id = employee.contract_id.salary_level_id.id

    @api.onchange('new_job_grade_id', 'new_salary_level_id')
    def _onchange_job_grade_level(self):
        if self.new_job_grade_id and self.new_salary_level_id:
            salary = self.env['hr.salary'].search([('job_grade_id', '=', self.new_job_grade_id.id),
                                                   ('salary_level_id', '=', self.new_salary_level_id.id)], order='id desc', limit=1)
            if salary:
                self.new_wage = salary.salary
    
    @api.model
    def create(self, vals):
        employee = self.env['hr.employee'].browse(vals['employee_id'])
        vals['name'] = "Transfer Of " + employee.name
        transfer_no = self.env['ir.sequence'].next_by_code('transfer.code')
        if transfer_no:                          
            vals['transfer_no'] = transfer_no
        res = super(EmployeeTransfer, self).create(vals)
        return res
    
    def button_approve(self, employee_id=None):
        if not employee_id:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], order='id desc', limit=1).id
        self.approved_employee_id = employee_id
        self.employee_id.department_id = self.new_department_id.id
        self.employee_id.branch_id = self.new_branch_id
        self.employee_id.job_id = self.new_job_id.id
        self.employee_id.company_id = self.new_company_id.id
        contract = self.employee_id.contract_id
        contract_values = {'company_id': self.new_company_id.id,
                           'department_id': self.new_department_id.id,
                           'branch_id': self.new_branch_id.id,
                           'job_id': self.new_job_id.id,
                           'job_grade_id': self.new_job_grade_id.id,
                           'salary_level_id': self.new_salary_level_id.id,
                           'wage': self.new_wage,
                           'date_start': self.date,
                           'state': 'open',
                           'date_end': False,
                           'hr_responsible_id': self.env.uid}
        if contract:
            contract.write({'state': 'close', 'date_end': self.date - timedelta(days=1)})
            new_contract = contract.copy(contract_values)
        else:
            contract_values.update({'employee_id': self.employee_id.id,
                                    'name': 'Contract of ' + self.employee_id.name,
                                    'resource_calendar_id': self.employee_id.resource_calendar_id and self.employee_id.resource_calendar_id.id or False})
            new_contract = self.env['hr.contract'].create(contract_values)
        self.state = 'transfer'
        
    def cancel_request(self):
        self.state = 'cancel'

    def button_done(self):
        self.state = 'done'

    def button_draft(self):
        self.state = 'draft'
        
    def button_request(self, employee_id=None):
        if not employee_id:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], order='id desc', limit=1).id
        self.requested_employee_id = employee_id
        self.state = 'request'
