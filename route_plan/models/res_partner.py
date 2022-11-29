from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tyre_vendor = fields.Boolean('Is a Tyre Vendor')
    engine_oil_vendor = fields.Boolean('Is a Engine Oil Vendor')