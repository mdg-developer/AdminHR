from datetime import date, datetime, time
from odoo import models, fields, api
from pytz import timezone, UTC


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    work_entry_id = fields.One2many('hr.work.entry', 'attendance_id')


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    attendance_id = fields.Many2one('hr.attendance', string='Attendance', ondelete='cascade')


class Contract(models.Model):
    _inherit = 'hr.contract'

    analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag')

    def _generate_work_entries(self, date_start, date_stop):
        vals_list = []

        date_start = fields.Datetime.to_datetime(date_start)
        date_stop = datetime.combine(fields.Datetime.to_datetime(date_stop), datetime.max.time())

        for contract in self:
            vals_list.extend(contract._get_work_entries_values(date_start, date_stop))

        if not vals_list:
            return self.env['hr.work.entry']

        return self.env['hr.work.entry'].create(vals_list)

    def _get_work_entries_values(self, date_start, date_stop):
        vals_list = []

        for contract in self:
            contract_vals = []
            employee = contract.employee_id
            calendar = contract.resource_calendar_id
            resource = employee.resource_id
            tz = timezone(calendar.tz or 'Asia/Yangon')
            date_start = tz.localize(date_start.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)
            date_stop = tz.localize(date_stop.replace(tzinfo=None), is_dst=True).astimezone(tz=UTC)

            leaves = self.env['resource.calendar.leaves'].sudo().search([
                ('resource_id', 'in', [False, resource.id]),
                ('calendar_id', '=', calendar.id),
                ('date_from', '<', date_stop),
                ('date_to', '>', date_start)
            ])

            for leave in leaves:
                start = leave.date_from
                end = leave.date_to
                if not start < end:
                    continue

                if leave.holiday_id:
                    work_entry_type = leave.holiday_id.holiday_status_id.work_entry_type_id
                    if self.env['hr.work.entry'].search([('work_entry_type_id', '=', work_entry_type.id), ('leave_id', '=', leave.holiday_id.id)]):
                        continue
                else:
                    work_entry_type = leave.mapped('work_entry_type_id')

                contract_vals += [{
                    'name': "%s%s" % (work_entry_type.name + ": " if work_entry_type else "", employee.name),
                    'date_start': start,
                    'date_stop': end,
                    'work_entry_type_id': work_entry_type.id,
                    'employee_id': employee.id,
                    'leave_id': leave.holiday_id and leave.holiday_id.id,
                    'company_id': contract.company_id.id,
                    'state': 'draft',
                    'contract_id': contract.id,
                }]

            # default_work_entry_type = self.structure_type_id.default_work_entry_type_id
            # attendances = self.env['hr.attendance'].search([('employee_id', '=', contract.employee_id.id),
            #                                                 ('check_in', '>=', date_start),
            #                                                 ('check_out', '<=', date_stop),
            #                                                 ('state', 'in', ('approve', 'verify'))])
            #
            # for attendance in attendances.filtered(lambda a: not a.work_entry_id):
            #     work_entry_type_id = default_work_entry_type
            #     contract_vals += [{
            #         'name': "%s: %s" % (work_entry_type_id.name, employee.name),
            #         'date_start': attendance.check_in,
            #         'date_stop': attendance.check_out,
            #         'work_entry_type_id': work_entry_type_id.id,
            #         'employee_id': employee.id,
            #         'contract_id': contract.id,
            #         'company_id': contract.company_id.id,
            #         'attendance_id': attendance.id,
            #         'state': 'draft',
            #     }]
            vals_list += contract_vals
        return vals_list
