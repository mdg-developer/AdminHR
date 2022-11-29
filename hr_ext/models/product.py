from odoo import api, fields, models, tools, _

class ProductCategory(models.Model):
    _inherit = "product.category"
    
    out_of_pocket_expense = fields.Boolean(string='Out of Pocket Expense', default=False)
    travel_expense = fields.Boolean(string='Travel Expense', default=False)
    trip_expense = fields.Boolean(string='Trip Expense', default=False)
    vehicle_cost = fields.Boolean(string='Vehicle Cost', default=False)
    maintenance = fields.Boolean(string='Corrective', default=False)
    preventive = fields.Boolean(string='Preventive', default=False)
    hr = fields.Boolean(string='HR', default=False)
    admin = fields.Boolean(string='Admin', default=False)
    purchase = fields.Boolean(string='Purchase', default=False)
    is_vehicle_selected = fields.Boolean(string='Is Vehicle Selected?', default=False)
    travel_request = fields.Boolean(string='Travel Request', default=False)
    maintenance_type = fields.Selection([('corrective', 'Corrective'), ('preventive', 'Preventive')],
                                        string='Maintenance Type')
