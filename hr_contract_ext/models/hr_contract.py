from odoo import models, fields, api, _
from calendar import monthrange
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.osv import expression

class Contract(models.Model):    
    _inherit = 'hr.contract'    
    _description = 'Contract'           
    
    job_grade_id = fields.Many2one('job.grade', string='Job Grade')
    salary_level_id = fields.Many2one('salary.level', string='Salary Level')
    ot_duty_per_hour = fields.Float('Duty OT Rate', compute='_compute_ot_duty_rate')
    is_daily_wage = fields.Boolean('Daily Wage', copy=False)
    ot_allowance_per_day = fields.Float('OT Allowance')
    grade_salary = fields.Float()
    salary_changed = fields.Boolean(default=False, copy=False)
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure')
    branch_id = fields.Many2one('res.branch', string='Branch')
    trial_date_end = fields.Date('End of Trial Period', default=lambda self: (date.today()+relativedelta(months=+3)), required=True, readonly=False, help="End date of the trial period (if there is one).")
    hotel_allowance = fields.Float('Hotel Allowance')
    cooker = fields.Boolean("Kitchen Staff",default=False,copy=False)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type",tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    ferry_route_name = fields.Boolean('ferry', default=False)
    ferry_route_ta = fields.Boolean('ferry/ta', default=False)
    traveling_allowance = fields.Char('Travelling Allowance')

    @api.onchange('struct_id')
    def onchange_struct_id(self):
        if self.struct_id:
            self.structure_type_id = self.struct_id.type_id.id

    @api.onchange('job_grade_id', 'salary_level_id')
    def _onchange_job_grade_level(self):
        if self.job_grade_id and self.salary_level_id:
            salary = self.env['hr.salary'].search([('job_grade_id', '=', self.job_grade_id.id),('salary_level_id', '=', self.salary_level_id.id)])
            if salary:
                self.grade_salary = salary.salary
                self.wage = salary.salary
            ot_allowance_obj = self.env['ot.allowance'].search([('job_grade_id', '=', self.job_grade_id.id),('state', '=', 'approve')], order='id desc', limit=1)
            if ot_allowance_obj:
                self.ot_allowance_per_day = ot_allowance_obj.amount

    @api.onchange('wage')
    def onchange_wage(self):
        if self.wage != self.grade_salary:
            self.salary_changed = True
        else:
            self.salary_changed = False

    @api.depends('wage')
    def _compute_ot_duty_rate(self):
        for contract in self:
            today = fields.Date.today()
            days_of_month = monthrange(today.year, today.month)[1]
            if contract.wage:
                contract.ot_duty_per_hour = (contract.wage / days_of_month) / 8
            else:
                contract.ot_duty_per_hour = 0

    @api.onchange('date_start')
    def onchange_start_date(self):
        for record in self:
            if record.date_start:
                record.trial_date_end = record.date_start + relativedelta(months=+3)
    
    @api.constrains('employee_id', 'state', 'kanban_state', 'date_start', 'date_end')
    def _check_current_contract(self):
        """ Two contracts in state [incoming | open | close] cannot overlap """
        for contract in self.filtered(lambda c: (c.state not in ['draft', 'close', 'cancel'] or c.state == 'draft' and c.kanban_state == 'done') and c.employee_id):
            domain = [
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                '|',
                    ('state', 'in', ['open']),
                    '&',
                        ('state', '=', 'draft'),
                        ('kanban_state', '=', 'done') # replaces incoming
            ]

            if not contract.date_end:
                start_domain = []
                end_domain = ['|', ('date_end', '>=', contract.date_start), ('date_end', '=', False)]
            else:
                start_domain = [('date_start', '<=', contract.date_end)]
                end_domain = ['|', ('date_end', '>', contract.date_start), ('date_end', '=', False)]

            domain = expression.AND([domain, start_domain, end_domain])
            if self.search_count(domain):
                raise ValidationError(_('An employee can only have one contract at the same time. (Excluding Draft and Cancelled contracts)'))