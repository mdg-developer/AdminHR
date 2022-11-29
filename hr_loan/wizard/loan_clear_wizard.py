from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class LoanClearWizard(models.TransientModel):
    _name = 'loan.clear.wizard'
    _description = 'Loan Clear Wizard'

    @api.model
    def default_get(self, fields):
        res = super(LoanClearWizard, self).default_get(fields)
        if (not fields or 'loan_id' in fields) and 'loan_id' not in res:
            if self.env.context.get('active_id'):
                res['loan_id'] = self.env.context['active_id']
        return res

    loan_id = fields.Many2one('hr.loan', string='Loan', required=True)
    clear_date = fields.Date(string='Clear Payment Date', default=fields.Date.today())
    remark = fields.Text(string='Remark')

    def action_clear(self):
        loan_lines = self.env['hr.loan.line'].sudo().search([('loan_id', '=', self.loan_id.id)])
        if loan_lines:
            first_day_clear_month = self.clear_date.replace(day=1)
            for line in loan_lines:
                if line.date >= first_day_clear_month and line.state != 'paid':
                    line.write({
                        'state': 'clear',
                        'remark': self.remark,
                    })
            amount = 0
            for line in loan_lines:
                if line.state != 'clear':
                    amount += line.amount 
            self.loan_id.write({
                'total_amount': amount,
                'total_paid_amount': amount,
                'balance_amount': 0,
            })

