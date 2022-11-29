from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = "stock.move"
    requisition_line_id = fields.Many2one('requisition.line', 'Requisition Line', index=True)
    
    