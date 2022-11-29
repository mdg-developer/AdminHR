from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    reward_carried_forward = fields.Float('Carried Forward', compute='_compute_reward_total', compute_sudo=True)
    reward_this_year = fields.Float('This Year', compute='_compute_reward_total', compute_sudo=True)
    reward_total = fields.Float('Total', compute='_compute_reward_total', compute_sudo=True)

    def _compute_reward_total(self):
        today_date = fields.Date.today()
        fiscal_obj = self.env['account.fiscal.year'].sudo()
        reward_obj = self.env['hr.reward'].sudo()
        for rec in self:
            rec.reward_carried_forward = 0
            rec.reward_this_year = 0
            rec.reward_total = 0
            current_fiscal_year = fiscal_obj.search([('date_from', '<=', today_date),
                                                     ('date_to', '>=', today_date),
                                                     ('company_id', '=', rec.company_id.id)])
            carry_rewards = reward_obj.search([('employee_id', '=', rec.id),
                                                ('state', '=', 'approve'),
                                                ('fiscal_year', '=', current_fiscal_year.id),
                                                ('reward_type_id.carry_reward', '=', True)])
            current_rewards = reward_obj.search([('employee_id', '=', rec.id),
                                                ('state', '=', 'approve'),
                                                ('fiscal_year', '=', current_fiscal_year.id),
                                                ('reward_type_id.carry_reward', '!=', True)])
            rec.reward_carried_forward = sum([x.mark for x in carry_rewards])
            rec.reward_this_year = sum([x.mark for x in current_rewards])
            rec.reward_total = rec.reward_carried_forward + rec.reward_this_year
            
            # if current_fiscal_year:
            #     prev_fiscal_year = fiscal_obj.search([('date_from', '<', current_fiscal_year.date_to)], order='date_from desc', limit=1)
            #     if prev_fiscal_year:
            #         prev_rewards = self.env['hr.reward'].search([('employee_id', '=', rec.id),
            #                                                      ('date', '>=', prev_fiscal_year.date_from),
            #                                                      ('date', '<=', prev_fiscal_year.date_to)])
            #         prev_total = sum([pr.mark for pr in prev_rewards])
            #         if prev_total:
            #             rec.reward_carried_forward = prev_total / 2

            #     cur_rewards = self.env['hr.reward'].search([('employee_id', '=', rec.id),
            #                                                 ('date', '>=', current_fiscal_year.date_from),
            #                                                 ('date', '<=', current_fiscal_year.date_to)])
            #     rec.reward_this_year = sum([cr.mark for cr in cur_rewards])
            #     rec.reward_total = rec.reward_carried_forward + rec.reward_this_year
