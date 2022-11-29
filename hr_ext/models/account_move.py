from odoo import fields, models, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    source_doc = fields.Char(string='Source Doc', store=True)
    loan_ref = fields.Char(string='Loan Ref')
    purchase_user_id = fields.Many2one('res.users', copy=False, tracking=True,
        string='Purchase Representative',
        default=lambda self: self.env.user)
    
    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        ''' Load from either an old purchase order, either an old vendor bill.

        When setting a 'purchase.bill.union' in 'purchase_vendor_bill_id':
        * If it's a vendor bill, 'invoice_vendor_bill_id' is set and the loading is done by '_onchange_invoice_vendor_bill'.
        * If it's a purchase order, 'purchase_id' is set and this method will load lines.

        /!\ All this not-stored fields must be empty at the end of this function.
        '''
        if self.purchase_vendor_bill_id.vendor_bill_id:
            self.invoice_vendor_bill_id = self.purchase_vendor_bill_id.vendor_bill_id
            self._onchange_invoice_vendor_bill()
        elif self.purchase_vendor_bill_id.purchase_order_id:
            self.purchase_id = self.purchase_vendor_bill_id.purchase_order_id
        self.purchase_vendor_bill_id = False

        if not self.purchase_id:
            return

        # Copy partner.
        self.partner_id = self.purchase_id.partner_id
        self.fiscal_position_id = self.purchase_id.fiscal_position_id
        self.invoice_payment_term_id = self.purchase_id.payment_term_id
        self.currency_id = self.purchase_id.currency_id
        self.purchase_user_id = self.purchase_id.user_id
        self.branch_id = self.purchase_id.branch_id
        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.line_ids.mapped('purchase_line_id')
        new_lines = self.env['account.move.line']
        for line in po_lines.filtered(lambda l: not l.display_type):
            new_line = new_lines.new(line._prepare_account_move_line(self))
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()
            new_lines += new_line
        new_lines._onchange_mark_recompute_taxes()

        # Compute invoice_origin.
        origins = set(self.line_ids.mapped('purchase_line_id.order_id.name'))
        self.invoice_origin = ','.join(list(origins))

        # Compute ref.
        refs = set(self.line_ids.mapped('purchase_line_id.order_id.partner_ref'))
        refs = [ref for ref in refs if ref]
        self.ref = ','.join(refs)

        # Compute _invoice_payment_ref.
        if len(refs) == 1:
            self._invoice_payment_ref = refs[0]

        self.purchase_id = False
        self._onchange_currency()
        self.invoice_partner_bank_id = self.bank_partner_id.bank_ids and self.bank_partner_id.bank_ids[0]

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state')
    def _compute_amount(self):
        invoice_ids = [move.id for move in self if move.id and move.is_invoice(include_receipts=True)]
        self.env['account.payment'].flush(['state'])
        if invoice_ids:
            self._cr.execute(
                '''
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                        OR
                        (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                ''', [tuple(invoice_ids)]
            )
            in_payment_set = set(res[0] for res in self._cr.fetchall())
        else:
            in_payment_set = {}

        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.type == 'entry' else -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
            is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual

            # Compute 'invoice_payment_state'.
            if move.type == 'entry':
                move.invoice_payment_state = False
            elif move.state == 'posted' and is_paid:
                if move.id in in_payment_set:
                    move.invoice_payment_state = 'in_payment'
                else:
                    move.invoice_payment_state = 'paid'
                    if move.type == 'in_invoice':
                        travel_expense = self.env['hr.travel.expense'].search([('vendor_bill_id','=',move.id),('state','=','finance_approve')])
                        if travel_expense:
                            for expense in travel_expense:
                                expense.write({'state':'reconcile'})
            else:
                move.invoice_payment_state = 'not_paid'
                
    def post(self): 
        res = super(AccountMove, self).post()
        for move in self:
            if move.type == 'in_invoice':
                vehicle_id = move.purchase_id.vehicle_id
                for line in self.invoice_line_ids:
                    template_id = self.env['product.template'].search([('fuel_cost','=',True)])
                    # vehicle_id = self.env['fleet.vehicle'].search([('driver_id','=',line.move_id.partner_id.id)],limit=1)
                    if not vehicle_id:
                        break
                    
                    if line.product_id.categ_id.vehicle_cost == True:
                        if line.product_id.product_tmpl_id.fuel_cost == True:
                            fuel_obj = self.env['fleet.vehicle.log.fuel']
                            result = {
                                      'vehicle_id': vehicle_id.id,
                                      'liter': line.quantity,
                                      'price_per_liter': line.price_unit,
                                      'amount': line.quantity *line.price_unit,
                                      'date': line.move_id.invoice_date,
                                      'inv_ref': line.move_id.name,
                                      'vendor_id': line.move_id.partner_id.id,
                                      }
                            fuel_id = fuel_obj.sudo().create(result)
                        else:
                            fleet_cost_obj = self.env['fleet.vehicle.cost']
                            result = {
                                      'vehicle_id': vehicle_id.id,
                                      'amount': line.quantity *line.price_unit,
                                      'date': line.move_id.invoice_date,
                                      'vendor_bill_ref': move.name,
                                      'po_ref': move.purchase_id.name,
                                      }
                            fuel_cost_id = fleet_cost_obj.sudo().create(result)

                    if line.product_id.categ_id.is_vehicle_selected == True or move.purchase_id.line_id.vehicle_id: 
                        vals = {
                                    'vehicle_id': vehicle_id.id,
                                    'amount': line.quantity * line.price_unit,
                                    'date': line.move_id.invoice_date,
                                    'vendor_bill_ref': move.name,
                                    'po_ref': move.purchase_id.name,
                                }
                        self.env['fleet.vehicle.cost'].sudo().create(vals)
        return res       