from odoo import fields, models, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    def get_vehicle(self,line):
        vehicle_id = False
        if line.move_id.purchase_id.line_id.vehicle_id.id:
            vehicle_id = line.move_id.purchase_id.line_id.vehicle_id.id
            return vehicle_id
        admin_trip = self.env['admin.trip.expense'].search([('vendor_bill_id','=',line.move_id.id)])
        for trip_line in admin_trip.trip_expense_lines:
            if trip_line.vehicle_id.id:
                vehicle_id = trip_line.vehicle_id.id
                return vehicle_id
        pocket = self.env['hr.pocket.expense'].search([('vendor_bill_id','=',line.move_id.id)])
        for pocket_line in pocket.pocket_line:
            if pocket_line.vehicle_id.id:
                vehicle_id = pocket_line.vehicle_id.id
                return vehicle_id
        travel = self.env['hr.travel.expense'].search([('vendor_bill_id','=',line.move_id.id)])
        for expense_line in travel.travel_line:
            if expense_line.vehicle_id.id:
                vehicle_id = expense_line.vehicle_id.id
                return vehicle_id
        return vehicle_id  
    def post(self):
        result = super(AccountPayment, self).post()
        if self.invoice_ids:
            for inv in self.invoice_ids:
                for line in inv.invoice_line_ids:
                    if line.vehicle_id or line.product_id.categ_id.is_vehicle_selected == True:
                        vehicle_id = self.get_vehicle(line)
                        if not vehicle_id:
                            vehicle_id = line.purchase_line_id.order_id.vehicle_id.id
                        vals = {
                            'vehicle_id': vehicle_id,#line.move_id.purchase_id.line_id.vehicle_id.id, #line.vehicle_id.id,
                            'description': inv.name,
                            'amount': line.quantity * line.price_unit,
                            'date': line.move_id.invoice_date,
                            'vendor_bill_ref': inv.name,
                        }
                        self.env['fleet.vehicle.cost'].create(vals)
        return result
