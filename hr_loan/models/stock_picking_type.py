from odoo import fields, models, api, _
from werkzeug import url_encode
from odoo.exceptions import UserError, ValidationError

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"
    branch_id = fields.Many2one('res.branch', string='Branch')