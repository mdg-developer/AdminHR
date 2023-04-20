from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_round


class HRPocketExpense(models.Model):
    _name = 'hr.pocket.expense'    
    _description = "HR Pocket Expense"
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
        ], string='Status', required=True, readonly=True, copy=False, 
        default='draft')  
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    pocket_line = fields.One2many('hr.pocket.expense.line', 'line_id', string='Pocket Expense Lines', copy=True, auto_join=True)
    vendor_bill_id = fields.Many2one('account.move', string='Bill')
    enable_approval = fields.Boolean('Enable Approval', compute='_compute_enable_approval')
    enable_line_edit = fields.Boolean('Enable Line Edit', compute='_compute_enable_line_edit')
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
                
    def action_submit(self):
        if self.employee_id and self.employee_id.branch_id.manager_id:
            one_signal_values = {'employee_id': self.employee_id.branch_id.manager_id.id,
                                 'contents': _('OUT OF POCKET EXPENSE: %s submitted out of pocket expense.') % self.employee_id.name,
                                 'headings': _('WB B2B : OUT OF POCKET EXPENSE SUBMITTED')}
            # self.env['one.signal.notification.message'].create(one_signal_values)
        return self.write({'state': 'submit'})
    
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
                'name':self.number or '',
                'type' : 'out_refund',
                'invoice_date':self.date,
                'journal_id' : journal.id,
                #'branch_id':branch,
            })
            invoice_line_obj = self.env['account.move.line']
            for line in self.pocket_line:
                inv_id.write({'invoice_line_ids': [(0, None, {
                'product_id': line.product_id.id,
                'quantity': line.qty,
                'price_unit': line.price_unit,  # values.get('price'),
                'name': line.product_id.name,
                # 'account_id': line.categ_id.property_account_expense_categ_id.id or False,
                'account_id': line.product_id.property_account_expense_id.id or False,
                'name': line.description,
                'analytic_account_id': line.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids or [])],
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
        
    def action_approve(self):
        if self.employee_id:
            one_signal_values = {'employee_id': self.employee_id.id,
                                 'contents': _('OUT OF POCKET EXPENSE: %s approved out of pocket expense.') % self.employee_id.branch_id.manager_id.name,
                                 'headings': _('WB B2B : OUT OF POCKET EXPENSE APPROVED')}
            # self.env['one.signal.notification.message'].create(one_signal_values)
        return self.write({'state': 'approve'})
    
    def action_reject(self):
        return self.write({'state': 'draft'})
    
    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('hr.pocket.expense')
        return super(HRPocketExpense, self).create(vals)
    
    @api.constrains('pocket_line')
    def _constrains_pocket_line(self):
        if self.pocket_line:
#             emp_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', self.employee_id.id),
#                                                                 ('state', '=', 'open')], limit=1)
            employee_id = None
            if not self.mobile_user_id:
                employee_id = self.employee_id
            else:
                employee_id = self.mobile_user_id
            emp_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', employee_id.id),
                                                                  ('state', '=', 'open')], limit=1)
            for line in self.pocket_line:
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
                    

class HRPocketExpenseLine(models.Model):
    _name = 'hr.pocket.expense.line'
    
    line_id = fields.Many2one('hr.pocket.expense', string='Row Show Reference', required=True, ondelete='cascade', index=True, copy=False)
    #company_id = fields.Many2one('res.company', string='Company')
    company_id = fields.Many2one(related='line_id.company_id', store=True, readonly=True)
    date = fields.Date('Expense Date') 
    categ_id = fields.Many2one(
        'product.category', string='Expense Title',
        domain="[('out_of_pocket_expense', '=', True)]",
        change_default=True, ondelete='restrict')
    product_id = fields.Many2one(
        'product.product', string='Expense',
        change_default=True, ondelete='restrict')  # Unrequired company
    description = fields.Char('Description')
    qty = fields.Float('Quantity', required=True, digits='Expense Qty', default=0.0)
    price_unit = fields.Float('Unit Price', compute='_compute_price_unit', required=True,readonly=False, store=True, digits='Product Price', default=0.0)
    price_subtotal = fields.Float(compute='_compute_amount', string='Amount', readonly=False, store=True)
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
        company_id = self.company_id.id or self.env.company.id
        self.product_id = False
        print(self.line_id.company_id.id,self.env.company)
        domain = {'product_id': [('categ_id', '=', self.categ_id.id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]}
        result = {'domain': domain}
        return result
            
    @api.depends('qty', 'price_unit')
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = round(line.price_unit * line.qty)
            
    @api.depends('qty', 'price_subtotal')
    def _compute_price_unit(self):
        for line in self:
            if line.qty != 0:
                line.price_unit = line.price_subtotal / line.qty
        
