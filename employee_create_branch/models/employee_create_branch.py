from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    branch_ids = fields.Many2many('res.branch',  'branch_id',string='Branches')


