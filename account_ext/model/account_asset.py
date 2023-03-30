from odoo import models, fields, api, _

class AccountAsset(models.Model):
    _inherit = "account.asset"

    purchase_date = fields.Date('Purchase Date')


