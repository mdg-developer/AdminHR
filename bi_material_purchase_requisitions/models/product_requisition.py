from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class ProductTemplateRequisition(models.Model):
    _name = "product.requisition"
    
    name = fields.Char(string='Template Name')
    to_location = fields.Many2one('stock.location',string='To Location')
    from_location = fields.Many2one('stock.location',string='From Location')
    requisition_product_line_ids = fields.One2many('product.requisition.line','product_requisition_id',string="Product Requisition Line ID")
    active = fields.Boolean(String='Active',default=True)
    operation_type_id = fields.Many2one('stock.picking.type',string='Operation Type')
    branch_id = fields.Many2one('res.branch',string='Branch')
#     state = fields.Selection([
#                                 ('draft','Draft'),
#                                 ('confirm','Confirmed'),
#                                 ('use_template','Used Template'),
#                                 ('cancel','Cancel')],string='Stage',default="draft")
    
    
#     def action_confirm(self):
#         if self.state not in ('cancel'):
#             res = self.write({
#                                 'state':'confirm',
#                             })
#             return res          
#     
#     
#     def action_cancel(self):
#         res = self.write({
#                             'state':'cancel',
#                         })
#         return res      
#     
#     def unlink(self):
#         for data in self:
#             if data.state not in ('draft'):
#                 raise UserError(('You cannot delete which is not draft.'))    
#     
class ProductTemplateRequisitionLine(models.Model):
    _name = "product.requisition.line"    
    
    
    name = fields.Char(string='Template Name')
    product_id = fields.Many2one('product.template',string="Product")
    description = fields.Text(string="Description")
    qty = fields.Float(string="Quantity",default=1.0)
    uom_id = fields.Many2one('uom.uom',string="Unit Of Measure")
    product_requisition_id = fields.Many2one('product.requisition',string="Product Requisition Line")
    
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id.id
    
