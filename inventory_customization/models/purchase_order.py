from odoo import models, fields, api
from xmlrpc import client
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):

    _inherit = 'purchase.order.line'
    _description = 'Purcahse Order Line'

    @api.onchange('product_id')
    def onChangeProduct_id(self):
        domain = {}
        if self.product_id:
            base_uom = self.product_id.uom_id.id
            report_uom = self.product_id.report_uom_id.id
            domain['product_uom'] = [('id', 'in', (base_uom,report_uom))]
        else:
            domain['product_uom'] = []
        return {'domain': domain}



