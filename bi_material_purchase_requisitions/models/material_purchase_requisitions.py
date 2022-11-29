# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
import math
from odoo.exceptions import Warning
from odoo.exceptions import UserError

class MaterialPurchaseRequisition(models.Model):
    _name = "material.purchase.requisition"
    _rec_name = 'sequence'
    
    @api.model
    def _get_branch_id(self):
        return self._context.get('branch_id', self.env.user.branch_id.id)
    
    @api.model
    def create(self , vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('material.purchase.requisition') or '/'
        return super(MaterialPurchaseRequisition, self).create(vals)

    @api.model 
    def default_get(self, flds): 
        result = super(MaterialPurchaseRequisition, self).default_get(flds)
        #result['employee_id'] = self.env.user.partner_id.id
        result['requisition_date'] = datetime.now()
        return result       
        
    def confirm_requisition(self):
        res = self.write({
                            'state':'department_approval',
                            'confirmed_by_id':self.env.user.id,
                            'confirmed_date' : datetime.now()
                        })
        template_id = self.env['ir.model.data'].get_object_reference(
                                              'bi_material_purchase_requisitions',
                                              'email_employee_purchase_requisition')[1]
        email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        if template_id:
            values = email_template_obj.generate_email(self.id, fields=None)
            values['email_from'] = self.employee_id.work_email
            values['email_to'] = self.requisition_responsible_id.email
            values['res_id'] = False
            mail_mail_obj = self.env['mail.mail']
            #request.env.uid = 1
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                mail_mail_obj.send([msg_id])           
        return res

    
    def department_approve(self):
        res = self.write({
                            'state':'ir_approve',
                            'department_manager_id':self.env.user.id,
                            'department_approval_date' : datetime.now()
                        })
        template_id = self.env['ir.model.data'].get_object_reference(
                                              'bi_material_purchase_requisitions',
                                              'email_manager_purchase_requisition')[1]
        email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        if template_id:
            values = email_template_obj.generate_email(self.id, fields=None)
            values['email_from'] = self.env.user.partner_id.email
            values['email_to'] = self.employee_id.work_email
            values['res_id'] = False
            mail_mail_obj = self.env['mail.mail']
            #request.env.uid = 1
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                mail_mail_obj.send([msg_id])        
        return res  

    
    def action_cancel(self):
        res = self.write({
                            'state':'cancel',
                        })
        return res          

    
    def action_received(self):
        res = self.write({
                            'state':'received',
                            'received_date' : datetime.now()
                        })
        return res         

    
    def action_reject(self):
        res = self.write({
                            'state':'cancel',
                            'rejected_date' : datetime.now(),
                            'rejected_by' : self.env.user.id
                        })
        return res 

    
    def action_reset_draft(self):
        res = self.write({
                            'state':'new',
                        })
        return res 


    
    def action_approve(self):
        res = self.write({
                            'state':'approved',
                            'approved_by_id':self.env.user.id,
                            'approved_date' : datetime.now()
                        })
        template_id = self.env['ir.model.data'].get_object_reference(
                                              'bi_material_purchase_requisitions',
                                              'email_user_purchase_requisition')[1]
        email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        if template_id:
            values = email_template_obj.generate_email(self.id, fields=None)
            values['email_from'] = self.employee_id.work_email
            values['email_to'] = self.employee_id.work_email
            values['res_id'] = False
            mail_mail_obj = self.env['mail.mail']
            #request.env.uid = 1
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                mail_mail_obj.send([msg_id])         
        return res 

    
    def create_picking_po(self):
        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']
        for line in self.requisition_line_ids:
            product_id = self.env['product.product'].search([('product_tmpl_id','=',line.product_id.id)])
            if line.requisition_action == 'purchase_order':
                for vendor in line.vendor_id:
                    pur_order = purchase_order_obj.search([('requisition_po_id','=',self.id),('partner_id','=',vendor.id)])
                    if pur_order:
                        po_line_vals = {
                                        'product_id' : product_id.id,
                                        'product_qty': line.qty,
                                        'name' : line.description,
                                        'price_unit' : line.product_id.list_price,
                                        'date_planned' : datetime.now(),
                                        'product_uom' : line.uom_id.id,
                                        'order_id' : pur_order.id,
                        }
                        purchase_order_line = purchase_order_line_obj.create(po_line_vals)
                    else:
                        vals = {
                                'partner_id' : vendor.id,
                                'date_order' : self.requisition_date,#datetime.now(),
                                'date_approve' : self.requisition_date,
                                'requisition_po_id' : self.id,
                                'branch_id':self.branch_id.id, #or self.env.user.branch_id.id,
                                'state' : 'draft'
                        }
                        purchase_order = purchase_order_obj.create(vals)
                        po_line_vals = {
                                        'product_id' : product_id.id,
                                        'product_qty': line.qty,
                                        'name' : line.description,
                                        'price_unit' : line.product_id.list_price,
                                        'date_planned' : datetime.now(),
                                        'product_uom' : line.uom_id.id,
                                        'order_id' : purchase_order.id,
                        }
                        purchase_order_line = purchase_order_line_obj.create(po_line_vals)
            else:
                #for vendor in line.vendor_id:
                stock_picking_obj = self.env['stock.picking']
                stock_move_obj = self.env['stock.move']
                stock_picking_type_obj = self.env['stock.picking.type']
                picking_type_ids = stock_picking_type_obj.search([('code','=','internal')])
                if not picking_type_ids:
                    raise Warning(_('Please define Internal Picking.'))
                #employee_id = self.env['hr.employee'].search('id','=',self.env.user.name)
                #pur_order = stock_picking_obj.search([('requisition_picking_id','=',self.id),('partner_id','=',vendor.id)])
                pur_order = stock_picking_obj.search([('requisition_picking_id','=',self.id)],limit=1)
                if pur_order:
                    pic_line_val = {
                                    'name': product_id.name,
                                    'product_id' : product_id.id,
                                    'product_uom_qty' : line.qty,
                                    'picking_id' : pur_order.id,#stock_picking.id,
                                    'product_uom' : line.uom_id.id,
                                    'location_id': self.source_location_id.id,
                                    'location_dest_id' : self.destination_location_id.id,
                                    'requisition_line_id':line.id,
                                    #'branch_id':self.branch_id.id, #or self.env.user.branch_id.id,

                    }
                    stock_move = stock_move_obj.create(pic_line_val)

                else:
                    val = {
                            #'partner_id' : vendor.id,
                            'branch_id':self.branch_id.id, #or self.env.user.branch_id.id,
                            'location_id'  : self.source_location_id.id,
                            'location_dest_id' : self.destination_location_id.id,#picking_type_ids[0].default_location_dest_id.id,
                            'picking_type_id' : self.internal_picking_id.id,#picking_type_ids[0].id,
                            'company_id': self.env.user.company_id.id,
                            'requisition_picking_id' : self.id,
                            'scheduled_date': self.requisition_date,
                            'actual_date': self.requisition_date,
			#'material_requisition_id':self.job_order_id and self.job_order_id.id,
			#'job_order_user_id':self.job_order_user_id and self.job_order_user_id.id,
			#'construction_project_id':self.construction_project_id and self.construction_project_id.id,
			#'analytic_account_id':self.account_analytic_id and self.account_analytic_id.id,
                    }
                    stock_picking = stock_picking_obj.create(val)

                    pic_line_val = {
                                    #'partner_id' : vendor.id,
                                    'name': product_id.name,
                                    'product_id' : product_id.id,
                                    'product_uom_qty' : line.qty,
                                    'product_uom' : line.uom_id.id,
                                    'location_id': self.source_location_id.id,
                                    #'location_dest_id' : self.internal_picking_id.id,#picking_type_ids[0].default_location_dest_id.id,
                                    'location_dest_id' : self.destination_location_id.id,
                                    'picking_id' : stock_picking.id,
                                    'requisition_line_id':line.id,
                                    #'branch_id':self.branch_id.id, #or self.env.user.branch_id.id,

                    }
                    stock_move = stock_move_obj.create(pic_line_val)

        res = self.write({
                            'state':'po_created',
                        })
        return res                 

    
    def _get_internal_picking_count(self):
        for picking in self:
            picking_ids = self.env['stock.picking'].search([('requisition_picking_id','=',picking.id)])
            picking.internal_picking_count = len(picking_ids)
            
    
    def internal_picking_button(self):
        self.ensure_one()
        return {
            'name': 'Internal Picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('requisition_picking_id', '=', self.id)],
        }

    
    def _get_purchase_order_count(self):
        for po in self:
            po_ids = self.env['purchase.order'].search([('requisition_po_id','=',po.id)])
            po.purchase_order_count = len(po_ids)
            
    
    def purchase_order_button(self):
        self.ensure_one()
        return {
            'name': 'Purchase Order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'domain': [('requisition_po_id', '=', self.id)],
        }

    
    def _get_emp_destination(self):
        if not self.employee_id.destination_location_id:
            return 
        self.destination_location_id = self.employee_id.destination_location_id

    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]


    @api.model
    def _default_picking_internal_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'internal'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]

    sequence = fields.Char(string='Sequence', readonly=True,copy =False)
    employee_id = fields.Many2one('hr.employee',string="Employee",required=True)
    department_id = fields.Many2one('hr.department',string="Department",required=True)
    product_requistition_id = fields.Many2one('product.requisition',string="Product Requisition Template")
    requisition_responsible_id  = fields.Many2one('res.users',string="Requisition Responsible")
    requisition_date = fields.Date(string="Requisition Date",required=True)
    received_date = fields.Date(string="Received Date",readonly=True)
    requisition_deadline_date = fields.Date(string="Requisition Deadline")
    state = fields.Selection([
                                ('new','New'),
                                ('department_approval','Waiting Department Approval'),
                                ('ir_approve','Waiting IR Approved'),
                                ('approved','Approved'),
                                ('po_created','Purchase Order Created'),
                                ('received','Received'),
                                ('cancel','Cancel')],string='Stage',default="new")
    requisition_line_ids = fields.One2many('requisition.line','requisition_id',string="Requisition Line ID",copy=True)    
    confirmed_by_id = fields.Many2one('res.users',string="Confirmed By")
    department_manager_id = fields.Many2one('res.users',string="Department Manager")
    approved_by_id = fields.Many2one('res.users',string="Approved By")
    rejected_by = fields.Many2one('res.users',string="Rejected By")
    confirmed_date = fields.Date(string="Confirmed Date",readonly=True)
    department_approval_date = fields.Date(string="Department Approval Date",readonly=True)
    approved_date = fields.Date(string="Approved Date",readonly=True)
    rejected_date = fields.Date(string="Rejected Date",readonly=True)
    reason_for_requisition = fields.Text(string="Reason For Requisition")
#     source_location_id = fields.Many2one('stock.location',string="Source Location", related="internal_picking_id.default_location_dest_id")
#     destination_location_id = fields.Many2one('stock.location',string="Destination Location", related="internal_picking_id.default_location_src_id")
    source_location_id = fields.Many2one('stock.location',string="Source Location",required=True)
    destination_location_id = fields.Many2one('stock.location',string="Destination Location",required=True)
    internal_picking_id = fields.Many2one('stock.picking.type',string="Internal Picking", default=_default_picking_internal_type)
    internal_picking_count = fields.Integer('Internal Picking', compute='_get_internal_picking_count')
    purchase_order_count = fields.Integer('Purchase Order', compute='_get_purchase_order_count')
    company_id = fields.Many2one('res.company',string="Company",default=lambda self: self.env.company)
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', required=True, default=_default_picking_type)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    request_number = fields.Char(string='Request Number', readonly=True,copy =False)
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id or False
            self.branch_id = self.employee_id.branch_id.id or False
            
    @api.onchange('product_requistition_id')
    def onchange_product_requistition_id(self):
        if self.product_requistition_id:
            if self.product_requistition_id.branch_id:
                self.branch_id = self.product_requistition_id.branch_id.id or False 
            self.source_location_id = self.product_requistition_id.from_location.id
            self.destination_location_id = self.product_requistition_id.to_location.id
            if self.product_requistition_id.operation_type_id:
                self.internal_picking_id = self.product_requistition_id.operation_type_id.id or False
                self.branch_id = self.product_requistition_id.branch_id.id or False
            if self.product_requistition_id.to_location:
                to_ware_id = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.product_requistition_id.to_location.location_id.id)], limit=1)
                if to_ware_id:
                    #self.env.cr.execute("""select id from stock_picking_type where lower(name) like 'internal%' and default_location_dest_id in(select default_location_dest_id from stock_picking_type where lower(name) like 'internal%' and warehouse_id =%s)""", (to_ware_id.id,))
                    self.env.cr.execute("""select id from stock_picking_type where lower(code) like 'internal' and default_location_dest_id in(select default_location_dest_id from stock_picking_type where lower(code) like 'internal' and warehouse_id =%s)""", (to_ware_id.id,))
                    t_data = self.env.cr.fetchall()
                    if t_data :
                        transfer_picking_type_id = t_data[0][0]
                        if not self.internal_picking_id:
                            self.picking_type_id = transfer_picking_type_id
                    self.env.cr.execute("""select id from stock_picking_type where lower(code) like 'incoming' and default_location_dest_id in(select default_location_dest_id from stock_picking_type where lower(code) like 'incoming' and warehouse_id =%s)""", (to_ware_id.id,))
                    r_data = self.env.cr.fetchall()
                    if r_data :
                        receipt_picking_type_id = r_data[0][0]
                        self.picking_type_id = receipt_picking_type_id
                        #self.internal_picking_id = receipt_picking_type_id    
            if not self.requisition_line_ids:
                for line in  self.product_requistition_id.requisition_product_line_ids:
                    val = { 'product_id':line.product_id.id,
                            'qty':line.qty,
                            'description':line.description,
                            'uom_id':line.uom_id.id,
                            'preq_line_id':line.id,
                            'requisition_id': self.id
                                         }
                    self.env['requisition.line'].sudo().create(val)
            else:
                for line in  self.product_requistition_id.requisition_product_line_ids:
                    val = { 'product_id':line.product_id.id,
                            'qty':line.qty,
                            'description':line.description,
                            'uom_id':line.uom_id.id,
                            'preq_line_id':line.id,
                            'requisition_id': self.id
                                         }  
                    for line2 in self.requisition_line_ids:
                        if line2.preq_line_id!=line:
                            self.env['requisition.line'].sudo().write(val)
                        if line2.preq_line_id==line:
                            line2.update(val)
                        else:
                            line2.unlink() 
                
#             res = self.product_requistition_id.update({
#                             'state':'use_template',
#                         })
#             return res         
                

class RequisitionLine(models.Model):
    _name = "requisition.line"

    
    @api.onchange('product_id')
    def onchange_product_id(self):
        res = {}
        if not self.product_id:
            return res
        self.uom_id = self.product_id.uom_id.id
        self.description = self.product_id.name

    product_id = fields.Many2one('product.template',string="Product")
    description = fields.Text(string="Description")
    qty = fields.Float(string="Quantity",default=1.0)
    uom_id = fields.Many2one('uom.uom',string="Unit Of Measure")
    requisition_id = fields.Many2one('material.purchase.requisition',string="Requisition Line")
    requisition_action = fields.Selection([('purchase_order','Purchase Order'),('internal_picking','Internal Picking')],string="Requisition Action",default="internal_picking")
    vendor_id = fields.Many2many('res.partner',string="Vendors")
    preq_line_id = fields.Many2one('product.requisition.line',string="Requisition Line")
    move_ids = fields.One2many('stock.move', 'requisition_line_id', string='Stock Moves')
    qty_delivered = fields.Float('Delivered Quantity', copy=False, compute='_compute_qty_requisition', compute_sudo=True, store=True, digits='Product Unit of Measure', default=0.0)
    
    def _get_all_moves(self):
        all_moves = self.env['stock.move']
        

        for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id.product_tmpl_id):
            all_moves != move
            

        return all_moves
    
    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_requisition(self):        
        # import pdb
        # pdb.set_trace()
        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.requisition_action == 'internal_picking':
                qty = 0.0
                #all_moves = line._get_all_moves()
                for move in line.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and line.product_id == r.product_id.product_tmpl_id):
                    if move.state != 'done' or not move.picking_id.requisition_picking_id:
                        continue
                    if move.picking_id.picking_type_id.code=='internal':
                        if not move.origin_returned_move_id:
                            qty += move.product_uom_qty
                            line.qty_delivered = qty
                        else:
                             qty -= move.product_uom_qty
                             line.qty_delivered = qty
                             
                
                
                
                
class StockPicking(models.Model):      
    _inherit = 'stock.picking'

    requisition_picking_id = fields.Many2one('material.purchase.requisition',string="Purchase Requisition")
    
#     def update_receipt_actual_date(self):
#         
#         today_date = datetime.now()
#         pickings = self.env['stock.picking'].search([('x_studio_requisition_no','!=',False),
#                                                      ('state','!=','done'),
#                                                      ('picking_type_code','=','incoming')])        
#         for pick in pickings:            
#             pick.write({'actual_date':today_date})        

class PurchaseOrder(models.Model):      
    _inherit = 'purchase.order'    

    requisition_po_id = fields.Many2one('material.purchase.requisition',string="Purchase Requisition")
    
    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        
        
        if self.date_planned:
           
            return {
                'picking_type_id': self.picking_type_id.id,
                'partner_id': self.partner_id.id,
                'user_id': False,
                'date': self.date_order,
                'origin': self.name,
                'location_dest_id': self._get_destination_location(),
                'location_id': self.partner_id.property_stock_supplier.id,
                'company_id': self.company_id.id,
                'scheduled_date':self.date_planned,
                'actual_date':self.date_planned,
            }
        else:
            return {
                'picking_type_id': self.picking_type_id.id,
                'partner_id': self.partner_id.id,
                'user_id': False,
                'date': self.date_order,
                'origin': self.name,
                'location_dest_id': self._get_destination_location(),
                'location_id': self.partner_id.property_stock_supplier.id,
                'company_id': self.company_id.id,
                
            }
        
class HrEmployee(models.Model):      
    _inherit = 'hr.employee'        
    
    destination_location_id = fields.Many2one('stock.location',string="Destination Location")    

class HrDepartment(models.Model):      
    _inherit = 'hr.department'    

    destination_location_id = fields.Many2one('stock.location',string="Destination Location")    


    
