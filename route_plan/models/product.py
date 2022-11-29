from odoo import api, fields, models, tools, _

class ProductCategory(models.Model):
    _inherit = "product.category"
    
    delivery = fields.Boolean(string='Delivery', default=False)
    fuel = fields.Boolean(string='Fuel', default=False)
    day_trip = fields.Boolean(string='Day Trip', default=False)
    plan_trip = fields.Boolean(string='Plan Trip', default=False)
    company_id = fields.Many2one('res.company', string='Company')


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    exclude = fields.Boolean(string='Exclude', default=False)