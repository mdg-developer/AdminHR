from odoo import fields, models, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    travel_request_id = fields.Many2one('travel.request', string='Travel Request')
    
    def post(self):
        rec = super(AccountPayment, self).post()
        if self.travel_request_id and self.travel_request_id.state not in ('in_progress','cancel','done','verify','cancelled'):
            self.travel_request_id.state = 'advance_withdraw'
        
        ar_line = self.env['account.move.line'].search([('payment_id', '=', self.id), ('credit', '=', 0.0)])
        if ar_line:
            for line in ar_line:
                line.write({'name': 'Expense Advance'})
