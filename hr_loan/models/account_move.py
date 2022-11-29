from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    branch_id = fields.Many2one('res.branch', string='Branch')
    
    
