from odoo import _, api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    report_uom_id = fields.Many2one('uom.uom',string='Report Unit of Measure')