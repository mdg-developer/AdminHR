from odoo import fields, models, api, _


class OverTimeRequest(models.Model):
    _inherit = 'ot.request'

    def get_department_filter(self, **args):
        employee_id = args.get('employee_id', False)
        department_ids = self.env['hr.department'].sudo().browse()
        if employee_id:
            #employee_list = self.env['hr.employee'].sudo().browse(employee_id)
            #employees = self.env['hr.employee'].search([('approve_manager', '=', employee_id)])
            employee_list = self.env['hr.employee'].search([('approve_manager', '=', employee_id)])
#             if employees:
#                 employee_list += employees
            for emp in employee_list:
                if emp.department_id not in department_ids:
                    department_ids += emp.department_id
        return [{'id': dep.id, 'name': dep.name} for dep in department_ids]


