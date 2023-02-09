from odoo import fields, models,api, _


class StockLocationInherit(models.Model):
    _inherit = 'stock.location'
    _description = 'Stock Location'

    branch_id = fields.Many2one('res.branch', string='Branch')