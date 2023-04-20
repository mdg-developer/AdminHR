from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_round


class HRTravelExpense(models.Model):
    _name = 'hr.travel.expense'
    _description = "HR Travel Expense"
    _rec_name = 'number'
    _order = 'id desc'
    
    @api.depends('travel_line.price_subtotal')
    def _compute_amount(self):
        amount = 0
        for move in self:
            for line in move.travel_line:
                 
                amount += line.price_subtotal           
            move.total_expense = amount
            move.diff_amount = move.advanced_money - move.total_expense
            
    @api.depends('travel_id')
    def _compute_payment_amount(self):
        for data in self:
            if data.travel_id:      
                data.update({                
                    'payment_amount': data.travel_id.payment_id.amount if data.travel_id.payment_id else 0,
                })
            else:
                data.update({                
                    'payment_amount': 0,
                })
            
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
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    travel_id = fields.Many2one('travel.request', 'Travel Request', required=True, index=True)    
    travel_line = fields.One2many('hr.travel.expense.line', 'line_id', string='Travel Expense Lines', copy=True, auto_join=True)
    total_expense = fields.Float(compute='_compute_amount', string='Total Expense', readonly=True, store=True)
    diff_amount = fields.Float(compute='_compute_amount', string='Different Amount', readonly=True, store=True)
    advanced_money = fields.Float(string='Advanced Money', related='travel_id.total_advance')
    
    payment_id = fields.Many2one('account.payment',related='travel_id.payment_id', string='Payment')
    #payment_state = fields.Char(related='travel_id.payment_id.state', store=True, copy=False, index=True, readonly=False)
    payment_state = fields.Selection([
        ('draft', 'Draft'), ('posted', 'Validated'), ('sent', 'Sent'), ('reconciled', 'Reconciled'), ('cancelled', 'Cancelled')
    ], related='travel_id.payment_id.state', string='Payment Status', readonly=True, copy=False, store=True, default='draft')
    
    vendor_bill_id = fields.Many2one('account.move', string='Bill')
    invoice_payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid')],
        string='Payment',related='vendor_bill_id.invoice_payment_state', store=True, readonly=True, copy=False, compute='_compute_type_name'
        )
    enable_approval = fields.Boolean('Enable Approval', compute='_compute_enable_approval')
    enable_line_edit = fields.Boolean('Enable Line Edit', compute='_compute_enable_line_edit')
    payment_amount = fields.Float(compute='_compute_payment_amount', string='Payment Amount', readonly=True, store=True)
    mobile_user_id = fields.Many2one('hr.employee', 'Mobile User')
    
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

    @api.depends('state')
    @api.depends_context('uid')
    def _compute_enable_line_edit(self):
        for rec in self:
            rec.enable_line_edit = False
            if rec.state == 'draft':
                rec.enable_line_edit = True
            elif self.env.user.has_group('hr_expense.group_hr_expense_team_approver') and rec.state == 'approve':
                rec.enable_line_edit = True
    
    @api.depends('invoice_payment_state')
    def compute_expense_status(self):
        for rec in self:
            if rec.invoice_payment_state == 'paid':
                rec.state = 'reconcile'
                if rec.travel_id:
                    rec.travel_id.write({'state': 'done'})


    def action_submit(self):
        return self.write({'state': 'submit'})
    
    def open_payment_matching_screen(self):
        # Open reconciliation view for customers/suppliers
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
        
#         action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
#         action_context.update({'suspense_moves_mode': True})
#         if len(move_line_id)>0:
#             action_context.update({'statement_line_ids': move_line_id})
#         action_context.update({'partner_id': self.employee_id.address_home_id.commercial_partner_id.id})
#         action_context.update({'partner_name': self.employee_id.address_home_id.commercial_partner_id.name})
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'bank_statement_reconciliation_view',
#             'context': action_context,
#         } 
        analytic_tag_ids = self.env['account.analytic.tag'].search([('company_id','=',self.company_id.id)])
        analytic_account_id = False
        analytic_tag_ids = []
        if self.employee_id.branch_id:
            analytic_account_id = self.employee_id.branch_id.analytic_account_id.id or False
        if self.employee_id.department_id:
           analytic_tag_ids = [self.employee_id.department_id.analytic_tag_id.id or False] 
        
        action_context = {'active_model':'account.move.line','company_ids': [self.company_id.id],
                          'analytic_tag_ids':analytic_tag_ids, 'partner_ids': [self.employee_id.address_home_id.commercial_partner_id.id],
                          'analytic_account_id':analytic_account_id,
                          'mode': 'customers'}
          
        if len(move_line_id)>0:
            action_context.update({'active_ids': move_line_id})
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    def action_reconcile(self):
        self.state = 'reconcile'
        if self.travel_id:
            self.travel_id.write({'state':'done'})
    
    def action_finance_approve(self):
        invoice_obj = self.env['account.move']
        if self.employee_id.address_home_id.commercial_partner_id.property_account_receivable_id:
            partner_id = self.employee_id.address_home_id
            account_id = self.employee_id.address_home_id.commercial_partner_id.property_account_receivable_id
            if not account_id:
                raise UserError(_('Please define customer account.'))
            company_id = self.company_id.id#self._context.get('company_id', self.env.user.company_id.id)
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
                'name': self.number,
                'type': 'out_refund',
                'invoice_date':self.date,
                'journal_id' : journal.id,
                #'branch_id':branch,
            })
            invoice_line_obj = self.env['account.move.line']
            
            for line in self.travel_line:
                inv_id.write({'invoice_line_ids': [(0, None, {
                'product_id': line.product_id.id,
                'quantity': line.qty,
                'price_unit': line.price_unit,  # values.get('price'),
                'name': line.product_id.name,
                # 'account_id': line.categ_id.property_account_expense_categ_id.id or False,
                'account_id': line.product_id.property_account_expense_id.id or False,
                'analytic_account_id': line.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids or [])],
                'name': line.description,
                # 'uom_id' : product_uom.id,
                'price_subtotal': line.qty * line.price_unit,  # values.get('price') * values.get('quantity'),
                'move_id': inv_id.id,
                'vehicle_id': line.vehicle_id.id,
            })]})
            inv_id.action_post()
            self.write({'vendor_bill_id':inv_id.id})
        else:                       
            raise UserError(_('Please define customer account.'))  
        return self.write({'state': 'finance_approve'})

    def _create_approved_notification_message(self, employee=None):
        if employee:
            one_signal_values = {'employee_id': employee.id,
                                 'contents': _('TRAVEL REQUEST : approved travel expense.'),
                                 'headings': _('WB B2B : APPROVED TRAVEL EXPENSE')}
            self.env['one.signal.notification.message'].create(one_signal_values)
    
    def action_approve(self):
        self.write({'state': 'approve'})
        # self._create_approved_notification_message(self.employee_id)
        # if self.employee_id.approve_manager:
        #     self._create_approved_notification_message(self.employee_id.approve_manager)
    
    def action_reject(self):
        return self.write({'state': 'draft'})
    
    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('hr.travel.expense')
        res = super(HRTravelExpense, self).create(vals)
        res.travel_id.state = 'in_progress'
        return res

    def write(self, vals):
        res = super(HRTravelExpense, self).write(vals)
        
        return res

    @api.constrains('travel_line')
    def _constrains_travel_line(self):
        if self.travel_line:
#             emp_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', self.employee_id.id),
#                                                                 ('state', '=', 'open')], limit=1)
            employee_id = None
            if not self.mobile_user_id:
                employee_id = self.employee_id
            else:
                employee_id = self.mobile_user_id
            emp_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', employee_id.id),
                                                                  ('state', '=', 'open')], limit=1)
            for line in self.travel_line:
                analyst_list = []
                if line.expense_title == 'Vehicle Operation Expenses' and line.expense == 'Fuel' and not line.vehicle_id:
                    raise ValidationError("Please choose vehicle!")
                if not line.analytic_account_id:
                    if not line.line_id.mobile_user_id:
                        line.analytic_account_id = line.line_id.employee_id.branch_id.analytic_account_id.id
                    else:
                        line.analytic_account_id = line.line_id.mobile_user_id.branch_id.analytic_account_id.id
                if not line.analytic_tag_ids:
                    if emp_contract:
                        analyst_list.append(emp_contract.job_grade_id.analytic_tag_id.id)
#                     if line.line_id.employee_id.department_id.analytic_tag_id:
                    if employee_id.department_id.analytic_tag_id:
                        dep_analytic_tag = self.env['account.analytic.tag'].sudo().browse(employee_id.department_id.analytic_tag_id.id)
                        analyst_list.append(dep_analytic_tag.id)
                    if line.vehicle_id:
                        vehicle_license_tag = self.env['account.analytic.tag'].sudo().search([('name', '=', line.vehicle_id.license_plate),
                                                                                            ('branch_id', '=', line.vehicle_id.branch_id.id),
                                                                                            ('company_id', '=', line.vehicle_id.company_id.id)])
                        if vehicle_license_tag:
                            analyst_list.append(vehicle_license_tag.id)
                        for vehicle_tag in line.vehicle_id.tag_ids:
                            if line.vehicle_id.branch_id and line.vehicle_id.company_id:
                                analytic_tag = self.env['account.analytic.tag'].sudo().search(
                                    [('name', '=', vehicle_tag.name),
                                     ('branch_id', '=', line.vehicle_id.branch_id.id),
                                     ('company_id', '=', line.vehicle_id.company_id.id)])
                                if analytic_tag:
                                    analyst_list.append(analytic_tag.id)
                    if analyst_list:
                        analytic_tag_obj = self.env['account.analytic.tag'].sudo().browse(analyst_list)
                        line.analytic_tag_ids = [(6, 0, analytic_tag_obj.ids or [])]

class HRTravelExpenseLine(models.Model):
    _name = 'hr.travel.expense.line'
    
    @api.depends('qty', 'price_unit')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit 
            price_unit = round(line.price_unit * line.qty)          
            line.update({                
                'price_subtotal': price_unit,
            })           
                
    line_id = fields.Many2one('hr.travel.expense', string='Row Show Reference', required=True, ondelete='cascade', index=True, copy=False)
    #company_id = fields.Many2one('res.company', string='Company')
    company_id = fields.Many2one(related='line_id.company_id', store=True, readonly=True)
    date = fields.Date('Expense Date') 
    categ_id = fields.Many2one(
        'product.category', string='Expense Title',
        domain="[('travel_expense', '=', True)]",
        change_default=True, ondelete='restrict')
    product_id = fields.Many2one(
        'product.product', string='Expense',
        change_default=True, ondelete='restrict')  # Unrequired company
    description = fields.Char('Description')
    qty = fields.Float('Quantity', required=True, digits='Expense Qty', default=0.0)
    price_unit = fields.Float('Unit Price', required=True,readonly=False, digits='Product Price', default=0.0)
    price_subtotal = fields.Float(compute='_compute_amount', string='Amount', readonly=True, store=True)
    attached_file = fields.Binary(string="Attachment")
    attached_filename = fields.Char("Attachment Filename")
    expense_title = fields.Char(string='Expense Title', related='categ_id.name')
    expense = fields.Char(string='Expense', related='product_id.name')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    image1 = fields.Binary(string="Attachment")
    image1_filename = fields.Char("Attachment Filename")
    image2 = fields.Binary(string="Attachment")
    image2_filename = fields.Char("Attachment Filename")
    image3 = fields.Binary(string="Attachment")
    image3_filename = fields.Char("Attachment Filename")
    image4 = fields.Binary(string="Attachment")
    image4_filename = fields.Char("Attachment Filename")
    image5 = fields.Binary(string="Attachment")
    image5_filename = fields.Char("Attachment Filename")
    image6 = fields.Binary(string="Attachment")
    image6_filename = fields.Char("Attachment Filename")
    image7 = fields.Binary(string="Attachment")
    image7_filename = fields.Char("Attachment Filename")
    image8 = fields.Binary(string="Attachment")
    image8_filename = fields.Char("Attachment Filename")
    image9 = fields.Binary(string="Attachment")
    image9_filename = fields.Char("Attachment Filename")
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
        company_id = self.line_id.company_id.id or self.env.company.id
        self.product_id = False
        print(self.line_id.company_id.id,self.env.company)
        domain = {'product_id': [('categ_id', '=', self.categ_id.id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]}
        result = {'domain': domain}
        return result
        