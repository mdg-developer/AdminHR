from odoo import fields, models, api, _
from werkzeug import url_encode
from odoo.exceptions import UserError, ValidationError

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"
    branch_id = fields.Many2one('res.branch', string='Branch')