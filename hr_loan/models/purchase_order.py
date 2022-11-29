from odoo import api, fields, models, tools, _
from datetime import date, datetime, timedelta
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase

class Purchase(models.Model):    
    _inherit = 'purchase.order'    
    
    @api.model
    def _default_picking_type(self):
        return self._get_picking_type(self.env.context.get('company_id') or self.env.company.id) 
       
    loan_id = fields.Many2one('hr.loan', string='Loan')   
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')  
    branch_id = fields.Many2one('res.branch', string='Branch')
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', states=Purchase.READONLY_STATES, required=True, default=_default_picking_type, domain="[('warehouse_id.company_id', '=', company_id),('branch_id','=',branch_id)]",
        help="This will determine operation type of incoming shipment")    
    
    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return

        requisition = self.requisition_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = requisition.vendor_id
        payment_term = partner.property_supplier_payment_term_id

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition.with_context(force_company=self.company_id.id).get_fiscal_position(partner.id)
        fpos = FiscalPosition.browse(fpos)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id,
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        self.branch_id = requisition.branch_id.id
        
        if not self.origin or requisition.name not in self.origin.split(', '):
            if self.origin:
                if requisition.name:
                    self.origin = self.origin + ', ' + requisition.name
            else:
                self.origin = requisition.name
        self.notes = requisition.description
        self.date_order = fields.Datetime.now()

        if requisition.type_id.line_copy != 'copy':
            return

        # Create PO lines if necessary
        order_lines = []
        for line in requisition.line_ids:
            # Compute name
            product_lang = line.product_id.with_context(
                lang=partner.lang,
                partner_id=partner.id
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            if fpos:
                taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id)).ids
            else:
                taxes_ids = line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_po_id:
                product_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_po_id)
                price_unit = line.product_uom_id._compute_price(line.price_unit, line.product_id.uom_po_id)
            else:
                product_qty = line.product_qty
                price_unit = line.price_unit

            if requisition.type_id.quantity_copy != 'copy':
                product_qty = 0

            # Create PO line
            order_line_values = line._prepare_purchase_order_line(
                name=name, product_qty=product_qty, price_unit=price_unit,
                taxes_ids=taxes_ids)
            order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines
    
    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.read()[0]
        create_bill = self.env.context.get('create_bill', False)
        # override the context to get rid of the default filtering
        result['context'] = {
            'default_type': 'in_invoice',
            'default_company_id': self.company_id.id,
            'default_purchase_id': self.id,
            'default_branch_id': self.branch_id.id,
        }
        # choose the view_mode accordingly
        if len(self.invoice_ids) > 1 and not create_bill:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        else:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                result['views'] = form_view
            # Do not set an invoice_id if we want to create a new bill.
            if not create_bill:
                result['res_id'] = self.invoice_ids.id or False
        result['context']['default_origin'] = self.name
        result['context']['default_reference'] = self.partner_ref
        return result


    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id and self.company_id:
            warehouse_id = self.env['stock.warehouse'].search([('company_id','=',self.company_id.id),('branch_id','=',self.branch_id.id)],limit=1)
            if warehouse_id:
                picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id', '=', warehouse_id.id),('branch_id','=',self.branch_id.id)],limit=1)
                if not picking_type:
                    picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
                    #self.picking_type_id = picking_type[:1]
                else:
                    self.picking_type_id=picking_type.id
                
    @api.onchange('loan_id')
    def onchange_loan_id(self):
        if self.loan_id:
            self.partner_id = self.loan_id.employee_id.address_home_id
            loan_product = self.env['product.product'].search([('is_loan', '=', True), ('company_id', '=', self.loan_id.company_id.id)], limit=1)
            amount = self.loan_id.loan_amount
            if self.order_line:
                for line in self.order_line:
                    line.product_id = loan_product
                    line.name = loan_product.name
                    line.product_qty = 1.0
                    line.product_uom = loan_product.uom_id
                    line.price_unit = amount
                    line.date_planned = datetime.now()
            else:
                self.write({
                    'order_line': [(0, 0, {
                        'product_id': loan_product.id,
                        'name': loan_product.name,
                        'product_qty': 1.0,
                        'product_uom': loan_product.uom_id.id,
                        'price_unit': amount,
                        'date_planned': datetime.now()
                    })]
                })

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    categ_id = fields.Many2one('product.category', string="Category")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    @api.onchange('categ_id')
    def onchange_categ_id(self):
        if not self.categ_id:
            return
        company = self.company_id.id or self.order_id.company_id.id
        product_ids = self.env['product.product'].search([('categ_id','=',self.categ_id.id),('purchase_ok', '=', True),('company_id','=',company)])    
        return {'domain': {
                'product_id': [('id', 'in', product_ids.ids)]
            }}
        
class AccountMove(models.Model):
    _inherit = 'account.move'

    def post(self): 
        res = super(AccountMove, self).post()
        for move in self:
            if move.purchase_id:
                if move.purchase_id.loan_id:
                    move.purchase_id.loan_id.write({'state': 'verify'})
        return res