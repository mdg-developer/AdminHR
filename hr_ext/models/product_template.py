from odoo import api, fields, models, tools, _

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    fuel_cost = fields.Boolean(string='Fuel Cost', default=False)
    is_loan = fields.Boolean(string='Is a Loan?', default=False)
    is_ssb = fields.Boolean(string="SSB", default=False)
    is_tax = fields.Boolean(string="TAX", default=False)
    is_ot = fields.Boolean(string="OT", default=False)
    is_commision = fields.Boolean(string="Commision", default=False)
    is_tyre = fields.Boolean(string="Tyre", default=False)
    is_engine_oil = fields.Boolean(string="Engine Oil", default=False)