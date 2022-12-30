from odoo import fields, models, api, _
from odoo.osv import expression
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, safe_eval
from odoo.exceptions import UserError, ValidationError


class EmployeeJobBenefitLine(models.Model):
    _name = 'employee.job.benefit.line'
    _rec_name = 'emp_benefit_id'

    emp_benefit_id = fields.Many2one('hr.employee', string='Employee Benefit Reference', required=True,
                                     ondelete='cascade', index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Job', help="Job")
    date = fields.Date(string='Paid Date', help='Date')
    hand_over_date = fields.Date(string='Hand Over Date')
    benefit_id = fields.Many2one('hr.job.benefit.config', 'Benefit')
    description = fields.Char('Description')
    quantity = fields.Float(string="Quantity")
    state = fields.Selection(
        [('pending', 'Pending'), ('on_hand', 'On Hand'), ('paid', 'Paid'), ('hand_over', 'Hand Over')],
        string="Status", default='pending', required=True, readonly=False, copy=False)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment')

    @api.onchange('emp_benefit_id')
    def onchange_employee(self):
        if self.emp_benefit_id:
            self.company_id = self.emp_benefit_id.company_id
            self.branch_id = self.emp_benefit_id.branch_id
            self.department_id = self.emp_benefit_id.department_id
            self.job_id = self.emp_benefit_id.job_id

    def action_on_hand(self):
        self.state = 'on_hand'

    def action_paid(self):
        if not self.date:
            raise ValidationError(_('Please choose paid date first.'))
        else:
            self.state = 'paid'

    def action_hand_over(self):
        if not self.hand_over_date:
            self.write({'hand_over_date': fields.Date.today()})
            # raise ValidationError(_('Please choose hand over date first.'))
        else:
            self.write({'hand_over_date': fields.Date.today()})
            self.state = 'hand_over'

class Employee(models.Model):
    _inherit = 'hr.employee'

    ssb_no = fields.Char('SSB No')
    ssb_issue_date = fields.Date('SSB Card Issue Date')
    ssb_temporary_card = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default=False, string='Temporary Card (yes/no)')
    ssb_temporary_card_no = fields.Char('Temporary Card Number')
    smart_card = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default=False, string='Smart Card (yes/no)')
    smart_card_issue_date = fields.Date('Smart Card Issue Date')
    smart_card_no = fields.Char('Smart Card Number')
    insurance_no = fields.Char('Insurance No')
    current_address = fields.Char('Current Address')
    insurance_company = fields.Char('Insurance Company Info')
    insurance_type_id = fields.Many2one('insurance.type', string='Insurance Type')
    employee_insurance = fields.Float('Employee Insurance (%)')
    employer_insurance = fields.Float('Employer Insurance (%)')
    insurance_start_date = fields.Date('Insurance Start Date')
    insurance_end_date = fields.Date('Insurance End Date')
    insurance_tax_exemption = fields.Boolean(string='Tax Exemption for Insurance', default=False)
    dotted_line_manager_id = fields.Many2one('hr.employee', string='Dotted Line Manager', check_company=False)
    dotted_child_ids = fields.One2many('hr.employee', 'dotted_line_manager_id', string='Direct dotted subordinates')
    benefit_line = fields.One2many('employee.job.benefit.line', 'emp_benefit_id', string='Order Lines', copy=True,
                                   auto_join=True)
    name_in_mm = fields.Char('Name (in Myanmar)')
    approve_manager = fields.Many2one('hr.employee', string='Approve Manager', check_company=False,track_visibility='always')
    is_branch_manager = fields.Boolean(default=False, copy=False)
    is_top = fields.Boolean('Top', default=False)
    department_id = fields.Many2one('hr.department', string='Department', domain="[('branch_id', '=', branch_id)]")
    job_id = fields.Many2one('hr.job', string='Job Position')
    job_grade_id = fields.Many2one('job.grade', string='Job Grade', related='job_id.job_grade_id', store=True, readonly=0)
    qualification = fields.Char('Qualification')

    # Default
    allow_leave_request = fields.Boolean('Leave Request', default=True, copy=False)
    allow_leave_report = fields.Boolean('Leave Report', default=True, copy=False)
    allow_attendance_report = fields.Boolean('Attendance Report', default=True, copy=False)
    allow_organization_chart = fields.Boolean('Organization Chart', default=True, copy=False)
    allow_pms = fields.Boolean('PMS', default=True, copy=False)
    allow_payslip = fields.Boolean('Payslip', default=True, copy=False)
    allow_loan = fields.Boolean('Loan', default=True, copy=False)
    allow_calendar = fields.Boolean('Calendar', default=True, copy=False)
    allow_reward = fields.Boolean('Reward', default=True, copy=False)
    allow_warning = fields.Boolean('Warning', default=True, copy=False)
    allow_overtime = fields.Boolean('Overtime', default=True, copy=False)
    allow_approval = fields.Boolean('Approval', default=True, copy=False)

    # Administration
    mobile_app_attendance = fields.Boolean('Mobile App Attendance', default=False, copy=False)
    allow_travel_request = fields.Boolean('Travel Request', default=False, copy=False)
    allow_insurance = fields.Boolean('Insurance', default=False, copy=False)
    allow_expense_claim = fields.Boolean('Expense Claim', default=False, copy=False)
    allow_expense_report = fields.Boolean('Expense Report', default=False, copy=False)
    allow_out_of_pocket = fields.Boolean('Out of Pocket', default=False, copy=False)
    allow_travel_expense = fields.Boolean('Travel Expense', default=False, copy=False)
    allow_document = fields.Boolean('Document', default=False, copy=False)
    # allow_advance_request = fields.Boolean('Advance Request', default=False, copy=False)

    # Fleet
    allow_fleet_info = fields.Boolean('Fleet Information', default=False, copy=False)
    allow_maintenance_request = fields.Boolean('Maintenance Request', default=False, copy=False)
    allow_plan_trip = fields.Boolean('Plan Trip (with Product)', default=False, copy=False)
    allow_plan_trip_waybill = fields.Boolean('Plan Trip (with Way Bill)', default=False, copy=False)
    allow_day_trip = fields.Boolean('Day Trip', default=False, copy=False)
    allow_employee_changes = fields.Boolean('Employee Changes', default=False, copy=False)

    ssb_not_calculate = fields.Boolean('SSB not calculate', default=False, copy=False)
    over_60_ssb = fields.Boolean('Over 60 SSB', default=False, copy=False)
    over_60_ssb_percent = fields.Float('Over 60 SSB Percent')
    no_need_attendance = fields.Boolean('No need attendance', default=False, copy=False)
    manager_job_id = fields.Many2one('hr.job', string='Manager Position')
    resign_date = fields.Date(string='Resign Date')
    cooker = fields.Boolean("Kitchen Staff",default=False,copy=False)
    if_exclude = fields.Boolean('Exclude Fingerpirnt ID', default=False, copy=False)
    address_home_id = fields.Many2one(
        'res.partner', 'Address', help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user,account.group_account_invoice,account.group_account_manager,account.group_account_user,fleet.fleet_group_user,purchase.group_purchase_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    
    extend_month = fields.Integer(string='Extend Month', readonly=True)
    extend_reason = fields.Text(string='Extend Reason', readonly=True)
    trial_end_date = fields.Date(string='Probation End Date', readonly=True)
    trial_date_after_extend = fields.Date(string='Probation End Date After Extension', readonly=True)

    employee_id_image = fields.Image(string='Employee ID Image')
    day_trip_id = fields.Many2one('day.plan.trip', string='Day Trip')
    plan_trip_waybill_id = fields.Many2one('plan.trip.waybill', string='Plan Trip Waybill')
    plan_trip_product_id = fields.Many2one('plan.trip.product', string='Plan Trip Product')
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    wage = fields.Monetary(string="Wage", related='contract_id.wage')
    
    @api.model
    def check_top_employee(self):
         
        records = self.env['hr.department'].search([('manager_id', '!=', False)])
        if records:
            for record in records:
                if record.manager_id.is_top == False:
                    record.manager_id.is_top = True
                    
    @api.onchange('department_id')
    def on_change_department_id(self):
        if self.department_id:
            self.manager_job_id = self.department_id.job_id.id if self.department_id.job_id else None

    def _sync_user(self, user):
        vals = dict(
            user_id=user.id,
        )
        return vals

    def _prepare_job_benefit_line(self, benefit):
        self.ensure_one()
        emp_id = False
        for emp_id in self.ids:
            emp_id = emp_id
        return {
            'emp_benefit_id': emp_id,
            'job_id': benefit.job_id.job_id.id,
            'benefit_id': benefit.benefit_id.id,
            'description': benefit.description,
            'quantity': benefit.qty,
            'state': 'pending',
        }

    @api.onchange('address_id')
    def _onchange_address(self):
        self.work_phone = self.address_id.phone
        
    @api.onchange('job_id')
    def _onchange_job_id(self):
        benefit_line = []
        res = []
        if self.job_id:
            emp_direct_mng = self.search(
                [('company_id', '=', self.company_id.id), ('branch_id', '=', self.branch_id.id),
                 ('job_id', '=', self.job_id.id)], limit=1)
            if emp_direct_mng:
                self.parent_id = emp_direct_mng.parent_id.id

            job_line = self.env['job.line'].sudo().search([('job_id', '=', self.job_id.id),
                                                                    ('company_id', '=', self.company_id.id),
                                                                    ('branch_id', '=', self.branch_id.id),
                                                                    ('department_id', '=', self.department_id.id)], limit=1)
            if job_line:
                self.manager_job_id = job_line.upper_position
                
            for emp_id in self.ids:
                benefits = self.env['employee.job.benefit.line'].search([('emp_benefit_id', '=', emp_id)])
                if len(benefits) > 0:
                    for job in self.env['employee.job.benefit.line'].search([('emp_benefit_id', '=', emp_id)]):
                        job.unlink()
            self.benefit_line = False

            for job_benefit in self.env['hr.job.benefit'].search([('job_id', '=', self.job_id.id)]):
                employee_id = False
                # for emp_id in self.ids:
                for benefit in job_benefit.benefit_line:
                    benefit_line_values = self._prepare_job_benefit_line(benefit)
                    benefit_line.append((0, 0, benefit_line_values))
                    # job_benefit = self.env['employee.job.benefit.line'].create({'emp_benefit_id':emp_id,'benefit':benefit.benefit,'description':benefit.description,'status':'pending'})
                    # emp_id.write({'benefit_line':[(0, None, {'emp_benefit_id':emp_id,'benefit':benefit.benefit,'description':benefit.description,'status':'pending'})]})
                    # res['benefit_line'].update({'emp_benefit_id':emp_id,'benefit':benefit.benefit,'description':benefit.description,'status':'pending'})
        self.benefit_line = benefit_line
    
    def toggle_active(self):
        res = super(Employee, self).toggle_active()
        self.message_post(subject="Active", body="Active: "+str(self.active))
        if self.active:
            latest_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', self.id), '|', ('active', '=', True), ('active', '=', False)], order='id desc', limit=1)
            latest_contract.write({
                'state': 'open',
                'active': True,
            })
        else:
            contracts = self.env['hr.contract'].sudo().search([('employee_id', '=', self.id)])
            if contracts:
                for contract in contracts:
                    contract.write({
                        'state': 'close',
                        'active': False,
                    })
        return res

    def one_signal_reminder(self, force_approve=False):
        domain = []
        
        get_date = datetime.today()
        #send passport reminder
        passport_expiry_date_add = self.env['ir.config_parameter'].sudo().get_param('passport_expiry_date')
        if passport_expiry_date_add:            

            passport_expiry_date = get_date + relativedelta(days=int(passport_expiry_date_add))
            passport_expiry_date = datetime.strftime(passport_expiry_date,'%Y-%m-%d')
            domain = [('passport_expiry_date', '=', passport_expiry_date)]
            employees = self.search(domain)
            for emp in employees:
                one_signal_values = {'employee_id': emp.id,
                      'message_type': 'reminder',
                     'contents': _('Passport Expiry Date for %s -%s') % (emp.name,emp.passport_expiry_date),
                     'headings': _('WB B2B : Employee Passport Expiry')}
                one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                if emp.branch_id.hr_manager_id:
                    one_signal_values = {'employee_id': emp.branch_id.hr_manager_id.id,
                      'message_type': 'reminder',
                     'contents': _('Passport Expiry Date for %s -%s') % (emp.name,emp.passport_expiry_date),
                     'headings': _('WB B2B : Employee Passport Expiry')}
                one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
        #send driver license expiry
        driver_license_expiry_date_add = self.env['ir.config_parameter'].sudo().get_param('driver_license_expiry_date')
        if driver_license_expiry_date_add:            

            driver_license_expiry_date = get_date + relativedelta(days=int(driver_license_expiry_date_add))
            driver_license_expiry_date = datetime.strftime(driver_license_expiry_date,'%Y-%m-%d')
            domain = [('dl_expired_date', '=', driver_license_expiry_date)]
            employees = self.search(domain)
            for emp in employees:
                one_signal_values = {'employee_id': emp.id,
                      'message_type': 'reminder',
                     'contents': _('Driving License Expiry Date for %s -%s') % (emp.name,emp.dl_expired_date),
                     'headings': _('WB B2B : Employee Driving License Expiry')}
                one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                if emp.branch_id.hr_manager_id:
#                 for incharge in self.env['fleet.vehicle'].search([('hr_driver_id','=',emp.id)]):
#                     if incharge.hr_manager_id:
                    one_signal_values = {'employee_id': emp.branch_id.hr_manager_id.id,
                  'message_type': 'reminder',
                 'contents': _('Driving License Expiry Date for %s -%s') % (emp.name,emp.dl_expired_date),
                 'headings': _('WB B2B : Employee Driving License Expiry')}
                    one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
        #send fleet license expiry
        fleet_license_expiry_date_add = self.env['ir.config_parameter'].sudo().get_param('fleet_license_expiry_date')
        if fleet_license_expiry_date_add:            

            fleet_license_expiry_date = get_date + relativedelta(days=int(fleet_license_expiry_date_add))
            fleet_license_expiry_date = datetime.strftime(fleet_license_expiry_date,'%Y-%m-%d')
            domain = [('license_expired_date', '=', fleet_license_expiry_date)]
            
            for fleet in self.env['fleet.vehicle'].search(domain):
                if fleet.hr_driver_id:
                    one_signal_values = {'employee_id': fleet.hr_driver_id.id,
                          'message_type': 'reminder',
                         'contents': _('Fleet License Expiry Date for %s -%s') % (fleet.hr_driver_id.name,fleet.license_expired_date),
                         'headings': _('WB B2B : Fleet License Expiry')}
                    one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                    
                    if fleet.hr_manager_id:
                        #for emp in self.env['hr.employee'].search([('user_id','=',fleet.manager_id.id)]):
                        one_signal_values = {'employee_id': fleet.hr_manager_id.id,
                          'message_type': 'reminder',
                         'contents': _('Fleet License Expiry Date for %s -%s') % (fleet.hr_driver_id.name,fleet.license_expired_date),
                         'headings': _('WB B2B : Fleet License Expiry')}
                        one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                        
        #send visa expiry
        visa_expiry_date_add = self.env['ir.config_parameter'].sudo().get_param('visa_expiry_date')
        if visa_expiry_date_add:            

            visa_expiry_date = get_date + relativedelta(days=int(visa_expiry_date_add))
            visa_expiry_date = datetime.strftime(visa_expiry_date,'%Y-%m-%d')
            domain = [('visa_expire', '=', visa_expiry_date)]
            employees = self.search(domain)
            for emp in employees:
                one_signal_values = {'employee_id': emp.id,
                      'message_type': 'reminder',
                     'contents': _('Visa Expire Date for %s -%s') % (emp.name,emp.visa_expire),
                     'headings': _('WB B2B : Employee Visa Expire')}
                one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values) 
                if emp.branch_id.hr_manager_id:
                    one_signal_values = {'employee_id': emp.branch_id.hr_manager_id.id,
                      'message_type': 'reminder',
                     'contents': _('Visa Expire Date for %s -%s') % (emp.name,emp.visa_expire),
                     'headings': _('WB B2B : Employee Visa Expire')}
                one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
        #send probation expiry
        probation_expiry_date_add = self.env['ir.config_parameter'].sudo().get_param('probation_expiry_date')
        if probation_expiry_date_add:            

            probation_expiry_date = get_date + relativedelta(days=int(probation_expiry_date_add))
            probation_expiry_date = datetime.strftime(probation_expiry_date,'%Y-%m-%d')
            domain = [('trial_date_end', '=', probation_expiry_date)]
            employees = self.env['hr.contract'].search(domain)
            for emp in employees:
                one_signal_values = {'employee_id': emp.employee_id.id,
                      'message_type': 'reminder',
                     'contents': _('Probation Expire Date for %s -%s') % (emp.name,emp.trial_date_end),
                     'headings': _('WB B2B : Probation Expire')}
                one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                if emp.branch_id.hr_manager_id:
                    one_signal_values = {'employee_id': emp.branch_id.hr_manager_id.id,
                      'message_type': 'reminder',
                     'contents': _('Probation Expire Date for %s -%s') % (emp.name,emp.trial_date_end),
                     'headings': _('WB B2B : Probation Expire')}
                    one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                if emp.employee_id.approve_manager:
                    one_signal_values = {'employee_id': emp.branch_id.approve_manager.id,
                      'message_type': 'reminder',
                     'contents': _('Probation Expire Date for %s -%s') % (emp.name,emp.trial_date_end),
                     'headings': _('WB B2B : Probation Expire')}
                    one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
        #send maintenance expiry
        maintenance_expiry_date_add = self.env['ir.config_parameter'].sudo().get_param('maintenance_expiry_date')
        if maintenance_expiry_date_add:            

            maintenance_expiry_date = get_date + relativedelta(days=int(maintenance_expiry_date_add))
            maintenance_expiry_date = datetime.strftime(maintenance_expiry_date,'%Y-%m-%d')
            domain = [('start_date', '>=', maintenance_expiry_date +' 00:00:00'),('start_date', '<=', maintenance_expiry_date +' 23:59:59'),('state','=','approved')]
            employees = self.env['maintenance.request'].search(domain)
            for emp in employees:
                if emp.driver_id:
                    one_signal_values = {'employee_id': emp.driver_id.id or False,
                          'message_type': 'reminder',
                         'contents': _('Maintenance Expire Date for %s -%s') % (emp.driver_id.name,emp.start_date),
                         'headings': _('WB B2B : Maintenance Expire')}
                    one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                if emp.driver_id.user_id:
                    
                    one_signal_values = {'employee_id': emp.driver_id.user_id.id or False,
                          'message_type': 'reminder',
                         'contents': _('Maintenance Expire Date for %s -%s') % (emp.driver_id.name,emp.start_date),
                         'headings': _('WB B2B : Maintenance Expire')}
                    one_signal_id = self.env['one.signal.notification.message'].create(one_signal_values)
                                  
        return True
    
    def generate_random_barcode(self):
        for employee in self:
            SequenceObj = self.env['ir.sequence']
            seq_no = SequenceObj.next_by_code('employee.badge')
            while True:
                self._cr.execute("select id from hr_employee where barcode = '%s'" % seq_no)
                if self._cr.fetchone():
                    seq_no = SequenceObj.next_by_code('employee.badge')
                else:
                    break
            employee.barcode = seq_no

    def name_get(self):
        self.browse(self.ids).sudo().read(['name', 'barcode'])
        return [(emp.id, '%s%s' % (emp.barcode and '[%s] ' % emp.barcode or '', emp.name)) for emp in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('barcode', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        account_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(account_ids).with_user(name_get_uid))

    def write(self, vals):
        for rec in self:
            old_approve_manager= rec.approve_manager.name or ''
            old_department_id = rec.department_id.name or ''
            old_job_id = rec.job_id.name or ''
            old_manager_id= rec.manager_job_id.name or ''
            old_dotted_line_manager_id = rec.dotted_line_manager_id.name or ''
        res = super(Employee, self).write(vals)
        # import pdb
        # pdb.set_trace()
        if vals.get('company_id'):
            company_id = self.env['res.company'].browse(vals['company_id'])
            if self.user_id:
                self.user_id.write({
                    'company_id': vals['company_id'],
                    'company_ids': [(6, 0, [x.id for x in company_id])]
                })
            self.address_home_id.company_id = vals['company_id']
        if vals.get('department_id'):
            department_id = self.env['hr.department'].browse(vals['department_id'])
            if department_id:
                self.message_post(body="Department "+old_department_id+"->"+department_id.name)
        if vals.get('approve_manager'):
            approve_manager = self.browse(vals['approve_manager'])
            if approve_manager:
                self.message_post(body="Approve Manager "+old_approve_manager+"->"+approve_manager.name)
        if vals.get('dotted_line_manager_id'):
            dotted_line_manager_id = self.browse(vals['dotted_line_manager_id'])
            if dotted_line_manager_id:
                self.message_post(body="Dotted Line Manager "+old_dotted_line_manager_id+"->"+dotted_line_manager_id.name)
        if vals.get('job_id'):
            job_id = self.env['hr.job'].browse(vals['job_id'])
            if job_id:
                self.message_post(body="Job Position "+old_job_id+"->"+job_id.name)
        if vals.get('manager_job_id'):
            manager_job_id = self.env['hr.job'].browse(vals['manager_job_id'])
            if manager_job_id:
                self.message_post(body="Manager Position "+old_manager_id+"->"+manager_job_id.name)

        return res

    def auto_archive_employee_resignation(self):
        employees = self.env['hr.employee'].sudo().search([('active', '=', True)])
        for emp in employees:
            if emp.resign_date and emp.resign_date <= fields.Date.today() and emp.active:
                contracts = self.env['hr.contract'].sudo().search([('employee_id', '=', emp.id)])
                if contracts:
                    for contract in contracts:
                        contract.write({
                            'state': 'close',
                            'active': False,
                        })
                #emp.write({'active': False})
                emp.toggle_active()
                emp.user_id.write({'active': False})
                emp.user_id = None


class HrEmployeePublic(models.Model):
    _inherit = ["hr.employee.public"]

    employee_id_image = fields.Image(string='Employee ID Image', compute='_compute_image', compute_sudo=True)

    branch_id = fields.Many2one('res.branch', compute='_compute_image', store= True)

    def _compute_image(self):
        for employee in self:
            # We have to be in sudo to have access to the images
            employee_id = self.sudo().env['hr.employee'].browse(employee.id)
            employee.image_1920 = employee_id.image_1920
            employee.image_1024 = employee_id.image_1024
            employee.image_512 = employee_id.image_512
            employee.image_256 = employee_id.image_256
            employee.image_128 = employee_id.image_128
            employee.employee_id_image = employee_id.employee_id_image
            employee.branch_id = employee_id.branch_id.id









