from odoo import fields, models, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    reference = fields.Char(string='Reference', readonly=True)
    day_trip_id = fields.Many2one('day.plan.trip', string='Day Trip Ref')
    plan_trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product Ref')
    plan_trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill Ref')
    
    def post(self):
        rec = super(AccountPayment, self).post()
        if self.day_trip_id and self.day_trip_id.state not in ('running','expense_claim','arrived','expense_submit','close','cancel','decline'):
            self.day_trip_id.state = 'advance_withdraw'
        if self.plan_trip_product_id and self.plan_trip_product_id.state not in ('running','expense_claim','arrived','expense_submit','close','cancel','decline'):
            self.plan_trip_product_id.state = 'advance_withdraw'
        if self.plan_trip_waybill_id and self.plan_trip_waybill_id.state not in ('running','in_progress','expense_claim','finance_approve','reconcile','done','close','cancel','decline'):
            self.plan_trip_waybill_id.state = 'advance_withdraw'
        
        ar_line = self.env['account.move.line'].search([('payment_id', '=', self.id), ('credit', '=', 0.0)])
        if ar_line:
            for line in ar_line:
                line.write({'name': 'Expense Advance'})
