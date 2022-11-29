from odoo import fields, models, api, _


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ['res.company','portal.mixin', 'mail.thread', 'mail.activity.mixin']

    managing_director_id = fields.Many2one('hr.employee', 'Managing Director',track_visibility="onchange")
    hr_employee_ids = fields.Many2many('hr.employee', string='HR', domain="[('company_id', '=', id)]")
    user_ids = fields.Many2many('res.users', 'res_company_users_custom_rel')
    name = fields.Char(track_visibility="onchange")
    street = fields.Char(track_visibility="onchange")
    street2 = fields.Char(track_visibility="onchange")
    zip = fields.Char(track_visibility="onchange")
    city = fields.Char(track_visibility="onchange")
    state_id = fields.Many2one(track_visibility="onchange")
    country_id = fields.Many2one(track_visibility="onchange")
