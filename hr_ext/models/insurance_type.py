from odoo import fields, models, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

class InsuranceType(models.Model):    
    _name = 'insurance.type'
    _description = 'Insurance Template' 
    _rec_name = 'policy_type'  
    
    policy_type = fields.Char(string='Policy Type', required=True)
    policy_number = fields.Integer(string='Policy Number')
    benefit = fields.Char(string='Benefits')
    policy_coverage = fields.Char(string='Policy Coverage')
    effective_date = fields.Date(string='Effective Date', required=True)
    expire_date = fields.Date(string='Expire Date', required=True)
    premium_amount = fields.Float(string='Premium Amount')
    coverage_amount = fields.Float(string='Coverage Amount')
    fees_employee = fields.Float(string='Premium Fees (Employee)')
    fees_employer = fields.Float(string='Premium Fees (Employer)')
    installment = fields.Integer(string="No of Installments", required=True, help="Number of installments")
    deduction_per_month = fields.Float(string='Deduction per month')
    attached_file = fields.Binary(string="Attachment", attachment=False)
    # attachment_id = fields.Many2many('ir.attachment', 'insurance_template_doc_rel', 'insurance_template_doc_id', 'insurance_template_attach_id4',
    #                                  string="Attachment", help='You can attach the copy of your Letter')

    @api.constrains('effective_date', 'expire_date', 'installment')
    def check_valid_date_range(self):
        for record in self:
            installment_duration = record.installment * 30
            today_date = datetime.today()
            last_date = today_date.date() + timedelta(days=installment_duration)
            if last_date > record.expire_date:
                raise ValidationError(_("Installment must be within the valid date!"))