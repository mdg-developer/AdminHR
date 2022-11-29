from odoo import api, fields, models


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    description = fields.Char('Description', required=True)
    remark = fields.Text('Remark')
    note = fields.Text(string='Note')
    company_id = fields.Many2one('res.company', 'Company')
    shift = fields.Boolean(string='Shift',default=False)
    is_management = fields.Boolean(string='Management', default=False)
    is_manager = fields.Boolean(string='Manager', default=False)
    is_staff = fields.Boolean(string='Staff', default=False)
    misc_journal_id = fields.Many2one('account.journal', 'Salary Rule Journal')
    logistics_commission_journal = fields.Many2one('account.journal', 'Logistics Commission Journal')
    meal_ot = fields.Boolean(string='Meal OT',default=False)
    
    @api.model
    def _get_default_rule_ids(self):
        return [
            (0, 0, {
                'name': 'Basic Salary',
                'sequence': 1,
                'code': 'BASIC',
                'category_id': self.env.ref('hr_payroll.BASIC').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': '''
calendar_days = payslip.days_of_month
if contract.is_daily_wage:
    attendance_days = worked_days.WORK100 and worked_days.WORK100.number_of_days or 0
    result = (contract.wage / calendar_days) * attendance_days
else:
    payslip_days = (payslip.date_to - payslip.date_from).days + 1
    if calendar_days != payslip_days:
        result = (contract.wage / calendar_days) * payslip_days
    else:
        result = contract.wage ''',
            }),
            (0, 0, {
                'name': 'Gross',
                'sequence': 100,
                'code': 'GROSS',
                'category_id': self.env.ref('hr_payroll.GROSS').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = categories.BASIC + categories.ALW',
            }),
            (0, 0, {
                'name': 'Net Salary',
                'sequence': 200,
                'code': 'NET',
                'category_id': self.env.ref('hr_payroll.NET').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = categories.BASIC + categories.ALW - categories.DED',
            })
        ]

    rule_ids = fields.One2many('hr.salary.rule', 'struct_id', string='Salary Rules', default=_get_default_rule_ids)

    def write(self, vals):
        if 'active' in vals:
            active = vals['active']
            for rule in self.env['hr.salary.rule'].search(['|', ('active', '=', True), ('active', '=', False), ('struct_id', '=', self.id)]):
                rule.write({'active': active})
        return super(HrPayrollStructure, self).write(vals)



class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    company_id = fields.Many2one('res.company', 'Company', related='struct_id.company_id')
    debit_account_misc = fields.Many2one('account.account', 'Debit Account')
    credit_account_misc = fields.Many2one('account.account', 'Credit Account')
    analytic_account_misc = fields.Many2one('account.analytic.account', 'Analytic Account')
    commission_debit_account = fields.Many2one('account.account', 'Debit Account')
    commission_credit_account = fields.Many2one('account.account', 'Credit Account')

    @api.model
    def _update_basic_salary_rule(self):
        update_code = '''
calendar_days = payslip.days_of_month
if contract.is_daily_wage:
    attendance_days = worked_days.WORK100 and worked_days.WORK100.number_of_days or 0
    result = (contract.wage / calendar_days) * attendance_days
else:
    payslip_days = (payslip.date_to - payslip.date_from).days + 1
    if calendar_days != payslip_days:
        result = (contract.wage / calendar_days) * payslip_days
    else:
        result = contract.wage '''
        basic_rules = self.search([('code', '=', 'BASIC')])
        for brule in basic_rules:
            brule.write({'amount_python_compute': update_code})
        self.env.cr.commit()
