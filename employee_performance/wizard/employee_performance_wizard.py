from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class employee_performance_wizard(models.TransientModel):
    _name = 'employee.performance.wizard'
    _description = 'Employee Performance Wizard'

    state = fields.Selection([('draft', 'Draft'), ('sent_to_employee', 'Sent To Employee'),
                              ('acknowledge', 'Acknowledge'), ('mid_year_self_assessment', 'Mid Year Self Assessment'),
                              ('mid_year_manager_approve', 'Mid Year Manager Approve'),
                              ('mid_year_dotted_manager_approve', 'Mid Year Dotted Manager Approve'),
                              ('mid_year_hr_approve', 'Mid Year HR Approve'),
                              ('year_end_self_assessment', 'Year End Self Assessment'),
                              ('year_end_manager_approve', 'Year End Manager Approve'),
                              ('year_end_dotted_manager_approve', 'Year End Dotted Manager Approve'),
                              ('sent_to_manager', 'Sent To Manager'), ('year_end_hr_approve', 'Year End HR Approve'),
                              ('cancel', 'Cancel')],
                             string='Status', required=True,
                             copy=False, default='draft')

    def change_state(self):
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids'))]
            for performance in self.env['employee.performance'].search(domain):
                performance.write({'state':self.state})