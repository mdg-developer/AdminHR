from odoo import _, api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    report_uom_id = fields.Many2one('uom.uom',string='Report Unit of Measure')