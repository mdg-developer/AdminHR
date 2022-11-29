from odoo import fields, models, api, _
from werkzeug import url_encode
from odoo.exceptions import UserError, ValidationError
    
class HrEmployee(models.Model):
    _inherit = "hr.employee"
 
    @api.model
    def create(self, values):
        # from hr module
        if values.get('user_id'):
            user = self.env['res.users'].browse(values['user_id'])
            values.update(self._sync_user(user))
            values['name'] = values.get('name', user.name)
         
        # from hr_holidays module
        if 'parent_id' in values:
            manager = self.env['hr.employee'].browse(values['parent_id']).user_id
            values['leave_manager_id'] = values.get('leave_manager_id', manager.id)
         
        # from res_nrc module
        if values.get('nrc_region_code') and values.get('nrc_prefix') and values.get('nrc_type') and values.get('nrc_number'):
            nrc_region_code = self.env['res.nrc.region'].browse(values['nrc_region_code'])
            nrc_prefix = self.env['res.nrc.prefix'].browse(values['nrc_prefix'])
            nrc_type = self.env['res.nrc.type'].browse(values['nrc_type'])
            values['nrc'] = nrc_region_code.name + '/' + nrc_prefix.name + '(' + nrc_type.name + ')' + str(values['nrc_number'])
        
        # from resource_mixin.py
        if not values.get('resource_id'):
            resource_vals = {'name': values.get(self._rec_name)}
            tz = (values.pop('tz', False) or
                  self.env['resource.calendar'].browse(values.get('resource_calendar_id')).tz)
            if tz:
                resource_vals['tz'] = tz
            resource = self.env['resource.resource'].create(resource_vals)
            values['resource_id'] = resource.id
            
        # from hr module
        employee = models.Model.create(self, values)
        url = '/web#%s' % url_encode({
            'action': 'hr.plan_wizard_action',
            'active_id': employee.id,
            'active_model': 'hr.employee',
            'menu_id': self.env.ref('hr.menu_hr_root').id,
        })
        employee._message_log(body=_('<b>Congratulations!</b> May I recommend you to setup an <a href="%s">onboarding plan?</a>') % (url))
        if employee.department_id:
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee.department_id.id)
            ])._subscribe_users()
         
        # from hr_resume.py
        resume_lines_values = []
        for emp in employee:
            line_type = self.env.ref('hr_skills.resume_type_experience', raise_if_not_found=False)
            resume_lines_values.append({
                'employee_id': emp.id,
                'name': emp.company_id.name or '',
                'date_start': emp.create_date.date(),
                'description': emp.job_title or '',
                'line_type_id': line_type and line_type.id,
            })
        self.env['hr.resume.line'].create(resume_lines_values)
        
        # from hr_ext module
        if values.get('company_id') and values.get('job_id'):
            job_id = self.env['hr.job'].sudo().browse(values['job_id'])
            job_line = self.env['job.line'].sudo().search([('job_id', '=', values['job_id']),
                                                            ('company_id', '=', values['company_id']),
                                                            ('branch_id', '=', values['branch_id']),
                                                            ('department_id', '=', values['department_id'])], limit=1)
            same_position_resign_employee = self.env['hr.employee'].sudo().search([('job_id', '=', values['job_id']),
                                                                                    ('company_id', '=', values['company_id']),
                                                                                    ('branch_id', '=', values['branch_id']),
                                                                                    ('department_id', '=', values['department_id']),
                                                                                    ('resign_date', '!=', False)])
            current_employee = self.search_count([('company_id', '=', values['company_id']),
                                                ('branch_id', '=', values['branch_id']),
                                                ('department_id', '=', values['department_id']),
                                                ('job_id', '=', values['job_id'])])
            if job_line.job_id.id == values['job_id'] and job_line.company_id.id == values['company_id'] and job_line.branch_id.id == values['branch_id'] and job_line.department_id.id == values['department_id']:
                current_employee = current_employee - 1
            if job_line and job_line.total_employee <= current_employee and not same_position_resign_employee:
                raise ValidationError(_('Cannot Create New Employee for %s Position. Expected New Employee Zero.') % (job_id.name))
        return employee
     
    def write(self, values):
        # from hr module
        if 'address_home_id' in values:
            account_id = values.get('bank_account_id') or self.bank_account_id.id
            if account_id:
                self.env['res.partner.bank'].browse(account_id).partner_id = values['address_home_id']
        if values.get('user_id'):
            values.update(self._sync_user(self.env['res.users'].browse(values['user_id'])))

        # from hr_holidays module
        if 'parent_id' in values:
            manager = self.env['hr.employee'].browse(values['parent_id']).user_id
            if manager:
                to_change = self.filtered(lambda e: e.leave_manager_id == e.parent_id.user_id or not e.leave_manager_id)
                to_change.write({'leave_manager_id': values.get('leave_manager_id', manager.id)})

        old_managers = self.env['res.users']
        if 'leave_manager_id' in values:
            old_managers = self.mapped('leave_manager_id')
            if values['leave_manager_id']:
                old_managers -= self.env['res.users'].browse(values['leave_manager_id'])
                
        res = models.Model.write(self, values)
        
        # remove users from the Responsible group if they are no longer leave managers
        old_managers._clean_leave_responsible_users()

        if 'parent_id' in values or 'department_id' in values:
            today_date = fields.Datetime.now()
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].sudo().search(['|', ('state', 'in', ['draft', 'confirm']), ('date_from', '>', today_date), ('employee_id', 'in', self.ids)])
            holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].sudo().search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            allocations.write(hr_vals)
        
        # from hr module
        if values.get('department_id') or values.get('user_id'):
            department_id = values['department_id'] if values.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users()
        
        # from hr_contract module
        if values.get('contract_id'):
            for employee in self:
                employee.resource_calendar_id.transfer_leaves_to(employee.contract_id.resource_calendar_id, employee.resource_id)
                employee.resource_calendar_id = employee.contract_id.resource_calendar_id

        # from hr_ext module
        if values.get('company_id'):
            company_id = self.env['res.company'].browse(values['company_id'])
            if self.user_id:
                self.user_id.write({
                    'company_id': values['company_id'],
                    'company_ids': [(6, 0, [x.id for x in company_id])]
                })
            self.address_home_id.company_id = values['company_id']
        
        # from res_nrc module
        if values.get('nrc_region_code') or values.get('nrc_prefix') or values.get('nrc_type') or values.get('nrc_number'):
            val_nrc_region_code = values['nrc_region_code'] if values.get('nrc_region_code') else self.nrc_region_code.id
            val_nrc_prefix = values['nrc_prefix'] if values.get('nrc_prefix') else self.nrc_prefix.id
            val_nrc_type = values['nrc_type'] if values.get('nrc_type') else self.nrc_type.id
            val_nrc_number = values['nrc_number'] if values.get('nrc_number') else self.nrc_number
            nrc_region_code = self.env['res.nrc.region'].browse(val_nrc_region_code)
            nrc_prefix = self.env['res.nrc.prefix'].browse(val_nrc_prefix)
            nrc_type = self.env['res.nrc.type'].browse(val_nrc_type)
            values['nrc'] = nrc_region_code.name + '/' + nrc_prefix.name + '(' + nrc_type.name + ')' + str(val_nrc_number)

        # from hr_ext module
        if 'company_id' in values or 'branch_id' in values or 'department_id' in values or 'job_id' in values:
            company_id = values['company_id'] if values.get('company_id') else self.company_id.id
            branch_id = values['branch_id'] if values.get('branch_id') else self.branch_id.id
            department_id = values['department_id'] if values.get('department_id') else self.department_id.id
            job_id = values['job_id'] if values.get('job_id') else self.job_id.id
            job = self.env['hr.job'].sudo().browse(job_id)
            job_line = self.env['job.line'].sudo().search([('job_id', '=', job_id),
                                                            ('company_id', '=', company_id),
                                                            ('branch_id', '=', branch_id),
                                                            ('department_id', '=', department_id)], limit=1)
            same_position_resign_employee = self.env['hr.employee'].sudo().search([('job_id', '=', job_id),
                                                                                    ('company_id', '=', company_id),
                                                                                    ('branch_id', '=', branch_id),
                                                                                    ('department_id', '=', department_id),
                                                                                    ('resign_date', '!=', False)])
            current_employee = self.search_count([('company_id', '=', company_id),
                                                ('branch_id', '=', branch_id),
                                                ('department_id', '=', department_id),
                                                ('job_id', '=', job_id),
                                                ('id', '!=', self.id)])
            if self._context.get('active_model') == 'hr.promotion':
                return res
            if job_line and job_line.total_employee <= current_employee and not same_position_resign_employee:
                raise ValidationError(_('Cannot Create New Employee for %s Position. Expected New Employee Zero.') % (job.name))
                
        return res
