from odoo import fields, models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):    
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"
    
    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
        return result
    
    def _compute_loan_amount(self):
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.state == 'paid':
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid

        # total_paid = 0.0
        # for loan in self:
        #     for line in loan.loan_lines:
        #         if line.paid:
        #             total_paid += line.amount
        #     payslip_obj = self.env['hr.payslip'].search([('state', '=', 'done'), ('employee_id', '=', loan.employee_id.id), ('company_id', '=', loan.company_id.id)])
        #     if payslip_obj:
        #         for line in payslip_obj.line_ids:
        #             if line.category_id.code == 'DED' and line.salary_rule_id.code in ('ELOAN', 'TLOAN'):
        #                 total_paid += line.total 
        #     balance_amount = loan.loan_amount - total_paid
        #     loan.total_amount = loan.loan_amount
        #     loan.balance_amount = balance_amount
        #     loan.total_paid_amount = total_paid    

    name = fields.Char(string="Loan Name", default="/", help="Name of the loan")
    date = fields.Date(string="Date", default=fields.Date.context_today, readonly=False, help="Date")
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company", default=lambda self: self.env.user.company_id,
                                 states={'draft': [('readonly', False)]})
    branch_id = fields.Many2one('res.branch', 'Branch', readonly=True, states={'draft': [('readonly', False)]}, domain="[('company_id', '=', company_id)]")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]", help="Employee")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True, string="Department", help="Employee")
    installment = fields.Integer(string="No of Installments", default=1, help="Number of installments")
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.context_today, help="Date of the paymemt")
    granter_id = fields.Many2many('hr.employee', string="Granter")
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    emp_account_id = fields.Many2one('account.account', string="Loan Account", domain="[('company_id', '=', company_id)]")
    treasury_account_id = fields.Many2one('account.account', string="Treasury Account", domain="[('company_id', '=', company_id)]")
    journal_id = fields.Many2one('account.journal', string="Journal", domain="[('company_id', '=', company_id)]")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency", default=lambda self: self.env.user.company_id.currency_id)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position", help="Job position")
    loan_amount = fields.Float(string="Loan Amount", required=True, help="Loan amount")
    total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_compute_loan_amount', help="Total loan amount")
    balance_amount = fields.Float(string="Balance Amount", store=True, compute='_compute_loan_amount', help="Balance amount")
    total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute='_compute_loan_amount', help="Total paid amount")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('verify', 'Verify'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', copy=False)

    type = fields.Selection([('training', 'Training'), ('others', 'Others')], string='Loan Type', default='others', required=True)
    enable_approval = fields.Boolean('Enable Approval', compute='_compute_enable_approval')
    attached_file = fields.Binary(string="Attachment", attachment=False)
    attached_filename = fields.Char("Loan Filename")
    move_id = fields.Many2one('account.move', string='Accounting Entry')

    @api.constrains('loan_lines')
    def onchange_loan_lines(self):
        for line in self.loan_lines:
            line.employee_id = self.employee_id

    @api.onchange('company_id')
    def onchange_company(self):
        if self.company_id:
            default_journal = self.env['account.journal'].search([('company_id', '=', self.company_id.id),
                                                                ('type', '=', 'general'),
                                                                ('is_loan_journal', '=', True)], limit=1)
            if default_journal:
                self.journal_id = default_journal
            default_loan_account = self.env['account.account'].search([('company_id', '=', self.company_id.id),
                                                                        ('code', '=', '118600')], limit=1)
            print('default loan : ', default_loan_account.id)
            if default_loan_account:
                self.emp_account_id = default_loan_account
            	
            default_treasury_account = self.env['account.account'].search([('company_id', '=', self.company_id.id),
                                                                        ('code', '=', '281002')], limit=1)
            print('default loan : ', default_treasury_account.id)
            if default_treasury_account:
                self.treasury_account_id = default_treasury_account

    @api.depends('employee_id')
    @api.depends_context('employee_id')
    def _compute_enable_approval(self):
        for req in self:
            if self.env.context.get('employee_id'):
                domain = [('id', '=', self.env.context.get('employee_id'))]
            else:
                domain = [('user_id', '=', self.env.user.id)]
            employee = self.env['hr.employee'].search(domain, limit=1)
            # if employee and req.employee_id.branch_id and req.employee_id.branch_id.manager_id == employee or employee.is_branch_manager and req.employee_id == employee:
            if employee and req.employee_id.branch_id and req.employee_id.branch_id.manager_id == employee:
                req.enable_approval = True
            else:
                req.enable_approval = False

    @api.model
    def create(self, values):
        loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', values['employee_id']), ('state', '=', 'approve'),
             ('balance_amount', '!=', 0)])
        if loan_count:
            raise ValidationError("The employee has already a pending installment")
        else:            
            values['name'] = self.env['ir.sequence'].sudo().next_by_code('hr.loan.seq') or ' '
            res = super(HrLoan, self).create(values)
            return res
    
    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
            loan._compute_loan_amount()
        return True
    
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_submit(self):
        self.write({'state': 'waiting_approval_1'})
#         req.employee_id.branch_id.manager_id
        if self.employee_id.branch_id and self.employee_id.branch_id.manager_id:
            one_signal_values = {'employee_id': self.employee_id.branch_id.manager_id.id,
                                 'contents': _('LOAN : %s submitted loan request.') % self.employee_id.name,
                                 'headings': _('WB B2B : SUBMITTED LOAN REQUEST')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        self.write({'state': 'approve'})
        self.create_account_draft_entry()
        if self.employee_id.branch_id.hr_manager_id:
            one_signal_values = {'employee_id': self.employee_id.id,
                                'contents': _('LOAN : %s approved loan request.') % self.employee_id.branch_id.manager_id.name,#self.employee_id.branch_id.hr_manager_id.name,
                                'headings': _('WB B2B : APPROVED LOAN REQUEST')}
            self.env['one.signal.notification.message'].create(one_signal_values)
            if self.employee_id.branch_id.manager_id != self.employee_id.branch_id.hr_manager_id:
                one_signal_values = {'employee_id': self.employee_id.branch_id.hr_manager_id.id,
                                     'contents': _(
                                         '%s LOAN : %s approved loan request.') % (self.employee_id.name,self.employee_id.branch_id.manager_id.name),
                                     # self.employee_id.branch_id.hr_manager_id.name,
                                     'headings': _('WB B2B : APPROVED LOAN REQUEST')}
                self.env['one.signal.notification.message'].create(one_signal_values)
        if self.create_uid:
            created_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.create_uid.id)], limit=1)
            if created_employee:
                one_signal_values = {'employee_id': created_employee.id,
                                    'contents': _('LOAN : %s approved loan request.') % self.employee_id.branch_id.manager_id.name,
                                    'headings': _('WB B2B : APPROVED LOAN REQUEST')}
                self.env['one.signal.notification.message'].create(one_signal_values)
        # for data in self:
        #     if not data.loan_lines:
        #         raise ValidationError("Please Compute installment")
        #     else:
        #         self.write({'state': 'approve'})
        #         if self.employee_id.branch_id.hr_manager_id:
        #             one_signal_values = {'employee_id': self.employee_id.id,
        #                                 'contents': _('LOAN : %s approved loan request.') % self.employee_id.branch_id.hr_manager_id.name,
        #                                 'headings': _('WB B2B : APPROVED LOAN REQUEST')}
        #             self.env['one.signal.notification.message'].create(one_signal_values)
                
    def action_verify(self):
        self.write({'state': 'verify'}) 
    
    def compute_amount(self):
        return self._compute_loan_amount()
               
    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel', 'refuse'):
                raise UserError(
                    'You cannot delete a loan which is not in draft or cancelled or refused state')
        return super(HrLoan, self).unlink()
    
    def create_account_draft_entry(self):
        if not self.journal_id:
            raise ValidationError(_('Please define misc account journal.'))
        move_dict = {
            'narration': '',
            'ref': self.name,
            'partner_id' : self.employee_id.address_home_id.id,
            'currency_id' : self.env.user.company_id.currency_id.id,
            'name': self.name or '',
            'date': self.date,
            'invoice_date': self.date,
            'journal_id' : self.journal_id.id,
        }
        debit_account_id = self.emp_account_id.id
        credit_account_id = self.treasury_account_id.id
        amount = self.loan_amount
        line_ids = []
        if debit_account_id: 
            debit = amount if amount > 0.0 else 0.0
            credit = -amount if amount < 0.0 else 0.0
            debit_line = {
                'account_id': debit_account_id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'debit': debit,
                'credit': credit,
                'exclude_from_invoice_tab': True
            }
            line_ids.append(debit_line)
        if credit_account_id:
            debit = -amount if amount < 0.0 else 0.0
            credit = amount if amount > 0.0 else 0.0
            credit_line = {
                'account_id': credit_account_id,
                'journal_id': self.journal_id.id,
                'date': self.date,
                'debit': debit,
                'credit': credit,
                'exclude_from_invoice_tab': True
            }
            line_ids.append(credit_line)
        move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
        move = self.env['account.move'].create(move_dict)      
        self.write({'move_id': move.id})  


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True, help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
    amount = fields.Float(string="Amount", required=True, help="Amount")
    paid = fields.Boolean(string="Paid", help="Paid")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", ondelete='cascade', help="Loan")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", help="Payslip")
    state = fields.Selection([('open', "Open"), ('paid', "Paid"), ('clear', "Clear")], default='open', string='Status')
    remark = fields.Text(string="Remark")

    


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

    loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')
