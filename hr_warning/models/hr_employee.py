from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    warning_carried_forward = fields.Float('Carried Forward', compute='_compute_warning_total', compute_sudo=True)
    warning_this_year = fields.Float('This Year', compute='_compute_warning_total', compute_sudo=True)
    warning_total = fields.Float('Total', compute='_compute_warning_total', compute_sudo=True)

    def _compute_warning_total(self):
        today_date = fields.Date.today()
        fiscal_obj = self.env['account.fiscal.year'].sudo()
        warning_obj = self.env['hr.warning'].sudo()
        for rec in self:
            rec.warning_carried_forward = 0
            rec.warning_this_year = 0
            rec.warning_total = 0
            current_fiscal_year = fiscal_obj.search([('date_from', '<=', today_date),
                                                     ('date_to', '>=', today_date),
                                                     ('company_id', '=', rec.company_id.id)])
            carry_warnings = warning_obj.search([('employee_id', '=', rec.id),
                                                ('state', '=', 'approve'),
                                                ('fiscal_year', '=', current_fiscal_year.id),
                                                ('warning_type_id.carry_warning', '=', True)])
            current_warnings = warning_obj.search([('employee_id', '=', rec.id),
                                                ('state', '=', 'approve'),
                                                ('fiscal_year', '=', current_fiscal_year.id),
                                                ('warning_type_id.carry_warning', '!=', True)])
            rec.warning_carried_forward = sum([x.mark for x in carry_warnings])
            rec.warning_this_year = sum([x.mark for x in current_warnings])
            rec.warning_total = rec.warning_carried_forward + rec.warning_this_year

            # if current_fiscal_year:
            #     prev_fiscal_year = fiscal_obj.search([('date_from', '<', current_fiscal_year.date_to)], order='date_from desc', limit=1)
            #     if prev_fiscal_year:
            #         prev_warnings = self.env['hr.warning'].search([('employee_id', '=', rec.id),
            #                                                        ('date', '>=', prev_fiscal_year.date_from),
            #                                                        ('date', '<=', prev_fiscal_year.date_to)])
            #         prev_total = sum([pw.mark for pw in prev_warnings])
            #         if prev_total:
            #             rec.warning_carried_forward = prev_total / 2

            #     cur_warnings = self.env['hr.warning'].search([('employee_id', '=', rec.id),
            #                                                   ('date', '>=', current_fiscal_year.date_from),
            #                                                   ('date', '<=', current_fiscal_year.date_to)])
            #     rec.warning_this_year = sum([cw.mark for cw in cur_warnings])
            #     rec.warning_total = rec.warning_carried_forward + rec.warning_this_year
