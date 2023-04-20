from odoo import models, fields, api, tools, _
from datetime import date, datetime, timedelta
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_round


class AdminTripExpense(models.Model):
    _name = 'admin.trip.expense'    
    _description = "Trip Expense"
    _rec_name = 'number'
    _order = 'id desc'

    number = fields.Char('Expense Code', default='New')
    date = fields.Date('Date')    
    employee_id = fields.Many2one('hr.employee', 'Employee')
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('submit', 'Submit'),
            ('approve', 'Manager Approve'),
            ('finance_approve', 'Finance Approve'),
            ('reconcile', 'Reconciled'),
            ('reject', 'Reject')
        ], string='Status', compute='compute_expense_status', required=True, readonly=True, copy=False, store=True,
        default='draft')  
    advanced_money = fields.Float(string='Advanced Money')
    source_doc = fields.Char(string='Source Doc', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    trip_expense_lines = fields.One2many('admin.trip.expense.line', 'expense_id', string='Trip Expense Lines', copy=True, auto_join=True)
    vendor_bill_id = fields.Many2one('account.move', string='Bill')
    daytrip_id = fields.Many2one('day.plan.trip', string='Day Trip')
    plantrip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip')
    plantrip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip')
    total_expense = fields.Float(compute='_compute_amount', string='Total Expense', readonly=True, store=True)
    diff_amount = fields.Float(compute='_compute_amount', string='Different Amount', readonly=True, store=True)
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    payment_state = fields.Selection([
        ('draft', 'Draft'), 
        ('posted', 'Validated'), 
        ('sent', 'Sent'), 
        ('reconciled', 'Reconciled'), 
        ('cancelled', 'Cancelled')
    ], related='payment_id.state', string='Payment Status', 
        readonly=True, copy=False, store=True, default='draft')
    payment_amount = fields.Float(string='Payment Amount', readonly=True, store=True)
    invoice_payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid')],
        string='Payment',related='vendor_bill_id.invoice_payment_state', 
        store=True, readonly=True, copy=False, compute='_compute_type_name')
    
    @api.depends('invoice_payment_state')
    def compute_expense_status(self):
        for rec in self:
            if rec.invoice_payment_state == 'paid':
                rec.state = 'reconcile'

    @api.depends('trip_expense_lines.price_subtotal')
    def _compute_amount(self):
        amount = 0
        for rec in self:
            for line in rec.trip_expense_lines:
                amount += line.price_subtotal           
            rec.total_expense = amount
            rec.diff_amount = rec.advanced_money - rec.total_expense

    def action_submit(self):
        if self.employee_id and self.employee_id.branch_id.manager_id:
            one_signal_values = {'employee_id': self.employee_id.branch_id.manager_id.id,
                                 'contents': _('TRIP EXPENSE: %s submitted trip expense.') % self.employee_id.name,
                                 'headings': _('WB B2B : TRIP EXPENSE SUBMITTED')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        return self.write({'state': 'submit'})
    
    def action_approve(self):
        if self.employee_id:
            one_signal_values = {'employee_id': self.employee_id.id,
                                 'contents': _('TRIP EXPENSE: %s approved trip expense.') % self.employee_id.branch_id.manager_id.name,
                                 'headings': _('WB B2B : TRIP EXPENSE APPROVED')}
            self.env['one.signal.notification.message'].create(one_signal_values)
        return self.write({'state': 'approve'})
    
    def action_reject(self):
        self.write({'state': 'reject'})
    
    def action_finance_approve(self):
        invoice_obj = self.env['account.move']
        if self.employee_id.address_home_id.commercial_partner_id.property_account_receivable_id:
            partner_id = self.employee_id.address_home_id
            account_id = self.employee_id.address_home_id.commercial_partner_id.property_account_receivable_id
            if not account_id:
                raise UserError(_('Please define Vendor account.'))
            company_id = self.company_id.id
            domain = [
                ('type', 'in', ['sale']),
                ('company_id', '=', company_id),
            ]
            journal = self.env['account.journal'].search(domain, limit=1)
            if not journal:
                raise UserError(_('Please define Journal.'))
            inv_id = invoice_obj.create({
                #'account_id' : account_id.id,
                'partner_id' : partner_id.id,
                'currency_id' : self.env.user.company_id.currency_id.id,
                'name':self.number or '',
                'type' : 'out_refund',#'in_invoice',
                'invoice_date':self.date,
                'journal_id' : journal.id,
            })
            invoice_line_obj = self.env['account.move.line']
            for line in self.trip_expense_lines:
                inv_id.write({'invoice_line_ids': [(0, None, {
                'product_id': line.product_id.id,
                'quantity': line.qty,
                'price_unit': line.price_unit,  
                'name': line.product_id.name,
                # 'account_id': line.categ_id.property_account_expense_categ_id.id or False,
                'account_id': line.product_id.property_account_expense_id.id or False,
                'name': line.description,
                'analytic_account_id': line.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids or [])],                
                'price_subtotal': line.qty * line.price_unit, 
                'move_id': inv_id.id,
            })]})
            inv_id.action_post()
            self.write({'vendor_bill_id': inv_id.id})
        else:            
            raise UserError(_('Please define Vendor account.')) 
        
        return self.write({'state': 'finance_approve'})

    def open_payment_matching_screen(self):
        move_line_id = []
        if self.payment_id:
            move_line = self.env['account.move.line'].search([('payment_id','=',self.payment_id.id)])
            for payment_line in move_line.filtered(lambda r: r.account_id.internal_type in ('receivable')).sorted(key='date_maturity'):
                if payment_line.move_id.state== 'posted':
                    move_line_id.append(payment_line.id)
        if self.vendor_bill_id:
            for bill_line in self.vendor_bill_id.line_ids.filtered(lambda r: r.account_id.internal_type in ('receivable')).sorted(key='date_maturity'):
                if bill_line.move_id.state == 'posted':
                    move_line_id.append(bill_line.id)

        if not self.employee_id.address_home_id:
            raise UserError(_("Payments without a customer can't be matched"))
        action_context = {'active_model':'account.move.line','company_ids': [self.company_id.id], 'partner_ids': [self.employee_id.address_home_id.commercial_partner_id.id], 'mode': 'customers'}
          
        if len(move_line_id)>0:
            action_context.update({'active_ids': move_line_id})
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('admin.trip.expense')
        return super(AdminTripExpense, self).create(vals)
    
    @api.constrains('trip_expense_lines')
    def _constrains_trip_expense_lines(self):
        if self.trip_expense_lines:
            emp_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', self.employee_id.id),
                                                                ('state', '=', 'open')], limit=1)
            for line in self.trip_expense_lines:
                analyst_list = []
                if not line.analytic_account_id:                    
                    line.analytic_account_id = line.expense_id.employee_id.branch_id.analytic_account_id.id
                if not line.analytic_tag_ids: 
                    if emp_contract:
                        analyst_list.append(emp_contract.job_grade_id.analytic_tag_id.id)
                    if line.expense_id.employee_id.department_id.analytic_tag_id:
                        dep_analytic_tag = self.env['account.analytic.tag'].sudo().browse(line.expense_id.employee_id.department_id.analytic_tag_id.id)
                        analyst_list.append(dep_analytic_tag.id)
                    if line.vehicle_id:
                        company_id = line.vehicle_id.company_id
                        branch_id = line.vehicle_id.branch_id
                        vehicle_license_tag = self.env['account.analytic.tag'].sudo().search([('name', '=', line.vehicle_id.license_plate),
                                                                                            ('branch_id', '=', branch_id.id),
                                                                                            ('company_id', '=', company_id.id)])
                        if vehicle_license_tag:
                            analyst_list.append(vehicle_license_tag.id)
                        for tag in line.vehicle_id.tag_ids:
                            if company_id and branch_id:
                                analytic_tag = self.env['account.analytic.tag'].sudo().search([('name', '=', tag.name),
                                                                                        ('company_id', '=', company_id.id),
                                                                                        ('branch_id', '=', branch_id.id)])
                                if analytic_tag:
                                    analyst_list.append(analytic_tag.id)
                    if analyst_list:
                        analytic_tag_obj = self.env['account.analytic.tag'].sudo().browse(analyst_list)        
                        line.analytic_tag_ids = [(6, 0, analytic_tag_obj.ids or [])]
                    

class AdminTripExpenseLine(models.Model):
    _name = 'admin.trip.expense.line'
    
    @api.depends('qty', 'price_unit')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit 
            price_unit = round(line.price_unit * line.qty)            
            line.update({                
                'price_subtotal': price_unit,
            })
            
    expense_id = fields.Many2one('admin.trip.expense', string='Trip Expense ID', required=True, ondelete='cascade', index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company')
    date = fields.Date('Expense Date') 
    categ_id = fields.Many2one(
        'product.category', string='Expense Title',
        change_default=True, ondelete='restrict')
    product_id = fields.Many2one(
        'product.product', string='Expense',
        change_default=True, ondelete='restrict')
    description = fields.Char('Description')
    qty = fields.Float('Quantity', required=True, digits='Expense Qty', default=0.0)
    price_unit = fields.Float('Unit Price', required=True,readonly=False, digits='Product Price', default=0.0)
    price_subtotal = fields.Float(compute='_compute_amount', string='Amount', readonly=True, store=True)
    over_amount = fields.Float('Over Amount')
    attached_file = fields.Binary(string="Attachment")
    expense_title = fields.Char(string='Expense Title', related='categ_id.name')
    expense = fields.Char(string='Expense', related='product_id.name')
    analytic_account_id  = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    attachment_include = fields.Boolean(string='Attachment Include?', default=False)
    
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        self.description = self.product_id.name
        self.price_unit = self.product_id.list_price
    
    @api.onchange('categ_id')
    def categ_id_change(self):
        if not self.categ_id:
            return
        company_id = self.expense_id.company_id.id or self.env.company.id
        self.product_id = False
        print(self.expense_id.company_id.id,self.env.company)
        domain = {'product_id': [('categ_id', '=', self.categ_id.id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]}
        result = {'domain': domain}
        return result    

class DayPlanTrip(models.Model):
    _inherit = 'day.plan.trip'

    trip_expense_id = fields.Many2one('admin.trip.expense', string='Trip Expense')
    day_trip_expense_id = fields.One2many('admin.trip.expense','daytrip_id')
    expense_status = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('approve', 'Manager Approve'),
        ('finance_approve', 'Finance Approve'),
        ('reconcile', 'Reconciled'),
        ('reject', 'Reject')
    ], string='Expense Status', related='trip_expense_id.state', readonly=True, store=True)


class PlanTripProduct(models.Model):
    _inherit = 'plan.trip.product'

    trip_expense_id = fields.Many2one('admin.trip.expense', string='Trip Expense', readonly=True)
    product_trip_expense_id = fields.One2many('admin.trip.expense','plantrip_product_id')
    expense_status = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('approve', 'Manager Approve'),
        ('finance_approve', 'Finance Approve'),
        ('reconcile', 'Reconciled'),
        ('reject', 'Reject')
    ], string='Expense Status', related='trip_expense_id.state', readonly=True, store=True)


class PlanTripWaybill(models.Model):
    _inherit = 'plan.trip.waybill'

    trip_expense_id = fields.Many2one('admin.trip.expense', string='Trip Expense', readonly=True)
    waybill_trip_expense_id = fields.One2many('admin.trip.expense','plantrip_waybill_id')
    expense_status = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('approve', 'Manager Approve'),
        ('finance_approve', 'Finance Approve'),
        ('reconcile', 'Reconciled'),
        ('reject', 'Reject')
    ], string='Expense Status', related='trip_expense_id.state', readonly=True, store=True)
