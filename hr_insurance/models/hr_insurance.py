from odoo import fields, models, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class Insurance(models.Model):    
    _name = 'hr.insurance'    
    _description = 'Insurance'    
    
    def _compute_insurance_amount(self):
        total_paid = 0.0
        for insurance in self:
            for line in insurance.insurance_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = insurance.premium_amount - total_paid
            insurance.total_amount = insurance.premium_amount
            insurance.balance_amount = balance_amount
            insurance.total_paid_amount = total_paid

    name = fields.Char(string='Name', readonly=True)
    employee_id = fields.Many2one('hr.employee',string='Employee Name', required=True)
    insurance_type_id = fields.Many2one('insurance.type', string='Policy Type', required=True)
    policy_number = fields.Integer(string='Policy Number', related='insurance_type_id.policy_number')
    benefit = fields.Char(string='Benefits', related='insurance_type_id.benefit')
    policy_coverage = fields.Char(string='Policy Coverage', related='insurance_type_id.policy_coverage')
    effective_date = fields.Date(string='Effective Date', related='insurance_type_id.effective_date')
    expire_date = fields.Date(string='Expire Date', related='insurance_type_id.expire_date')
    premium_amount = fields.Float(string='Premium Amount', related='insurance_type_id.premium_amount')
    coverage_amount = fields.Float(string='Coverage Amount', related='insurance_type_id.coverage_amount')
    fees_employee = fields.Float(string='Premium Fees (Employee)', related='insurance_type_id.fees_employee')
    fees_employer = fields.Float(string='Premium Fees (Employer)', related='insurance_type_id.fees_employer')
    installment = fields.Integer(string="No of Installments", related='insurance_type_id.installment', help="Number of installments")
    deduction_per_month = fields.Float(string='Deduction per month', related='insurance_type_id.deduction_per_month')
    # attachment_id = fields.Many2many('ir.attachment', 'insurance_doc_rel', 'insurance_doc_id', 'insurance_attach_id4',
    #                                  string="Attachment", help='You can attach the copy of your Letter')
    attached_file = fields.Binary(string="Attachment", attachment=False)
    insurance_lines = fields.One2many('hr.insurance.line', 'insurance_id', string="Insurance Line", index=True)
    total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_compute_insurance_amount', help="Total loan amount")
    balance_amount = fields.Float(string="Balance Amount", store=True, compute='_compute_insurance_amount', help="Balance amount")
    total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute='_compute_insurance_amount', help="Total paid amount")
    
    @api.constrains('effective_date', 'expire_date', 'installment')
    def check_valid_date_range(self):
        for record in self:
            installment_duration = record.installment * 30
            today_date = datetime.today()
            last_date = today_date.date() + timedelta(days=installment_duration)
            if last_date > record.expire_date:
                raise ValidationError(_("Installment must be within the valid date!"))
    
    def generate_insurance_lines(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for insurance in self:
            insurance.insurance_lines.unlink()
            date_start = datetime.strptime(str(insurance.effective_date), '%Y-%m-%d')
            # amount = insurance.premium_amount / insurance.installment
            amount = insurance.deduction_per_month
            for i in range(1, insurance.installment + 1):
                self.env['hr.insurance.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': insurance.employee_id.id,
                    'insurance_id': insurance.id})
                date_start = date_start + relativedelta(months=1)
            insurance._compute_insurance_amount()
        return True

    def action_claim_form(self):
        view = self.env.ref('hr_insurance.view_hr_claims_form')
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.claims',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'context': dict(self.env.context),
            'target': 'new',
        }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('insurance')
        res = super(Insurance, self).create(vals)
        return res

class InsuranceLine(models.Model):
    _name = "hr.insurance.line"
    _description = "Insurance Line"

    date = fields.Date(string="Payment Date", required=True, help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
    amount = fields.Float(string="Amount", required=True, help="Amount")
    paid = fields.Boolean(string="Paid", help="Paid")
    insurance_id = fields.Many2one('hr.insurance', string="Insurance Ref.", help="Insurance")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", help="Payslip")
    state = fields.Selection([('open', "Open"), ('paid', "Paid")], default='open', string='Status')
    payslip_input_id = fields.Many2one('hr.payslip.input')

class ClaimsInformation(models.Model):    
    _name = 'hr.claims'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Claims'    
    
    insurance_type_id = fields.Many2one('insurance.type', string='Insurance Type', required=True)
    name = fields.Char(string='Name', default='New')
    employee_id = fields.Many2one('hr.employee',string='Employee Name')
    insurance_id = fields.Many2one('hr.insurance', string='Insurance ID')
    date = fields.Date(string='Date')
    description = fields.Char(string="Field Description")
    claim_amount = fields.Float(string='Claim Amount')
    coverage_amount = fields.Float(string='Coverage Amount')
    balance = fields.Float(string="Balance", compute='compute_balance', store=True)
    attached_file = fields.Binary(string="Attachment", attachment=False)
    # attachment_id = fields.Many2many('ir.attachment', 'claim_doc_rel', 'claim_doc_id', 'claim_attach_id4',
    #                                  string="Attachment", help='You can attach the copy of your Letter')
    insurance_ids = fields.Many2many(
        'hr.insurance', 
        string='Insurances'
    )
    is_readonly = fields.Boolean(string='Is readonly?', default=False)
    
    @api.depends('claim_amount')
    def compute_balance(self):
        for rec in self:
            claim_objs = self.env['hr.claims'].search([('employee_id', '=', rec.employee_id.id),
                                                        ('insurance_id', '=', rec.insurance_id.id)])
            if claim_objs:
                total_claim_amount = 0.0
                for claim in claim_objs:
                    total_claim_amount += claim.claim_amount
                self.balance = self.coverage_amount - total_claim_amount 
            else:
                self.balance = self.coverage_amount - self.claim_amount

    @api.model
    def create(self, vals):
        vals['name'] = self.env['hr.employee'].browse(vals['employee_id']).name
        res = super(ClaimsInformation, self).create(vals)
        return res
    
class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_employee_insurance(self):

        self.insurance_count = self.env['hr.insurance'].search_count([('employee_id', '=', self.id)])

    insurance_count = fields.Integer(string="Insurance Count", compute='_compute_employee_insurance')


