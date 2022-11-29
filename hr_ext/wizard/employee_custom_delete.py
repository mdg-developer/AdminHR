from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class EmployeeCustomDelete(models.TransientModel):
    _name = 'employee.custom.delete'

    @api.model
    def default_get(self, fields):
        res = super(EmployeeCustomDelete, self).default_get(fields)
        if (not fields or 'employee_id' in fields) and 'employee_id' not in res:
            if self.env.context.get('active_id'):
                res['employee_id'] = self.env.context['active_id']
        return res

    date = fields.Date(string='Date', default=fields.Date.today())


    def action_delete(self):

        employee = self.env['hr.employee'].browse(self._context['active_id'])
        if employee:
            self.env.cr.execute("""delete from hr_employee where id in %s""", (tuple(employee.ids),))
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
