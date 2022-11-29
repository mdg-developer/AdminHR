from odoo import fields, models, api, _
from werkzeug import url_encode
from odoo.exceptions import UserError, ValidationError

class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"
    branch_id = fields.Many2one('res.branch', string='Branch')